"""Columnar precomputed structures, BM25F indexing, and fast filtering."""
import collections
import hashlib
import json
import math
import os
import pickle
import re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

from seo.normalize import normalize_text, tokenize_and_stem, light_stem
from seo.taxonomy import PRODUCT_TYPE_TO_FAMILIES
from seo.colors import COLOR_TO_BASE, get_base_color
from seo.mining import mine_attributes
from seo.aliases import (
    PRODUCT_TYPE_ALIASES, CATEGORY_ALIASES, AUDIENCE_ALIASES,
    COLOR_ALIASES, PATTERN_ALIASES
)

# BM25F field weights tuned for e-commerce search
FIELD_WEIGHTS = {
    "name": 3.5,
    "product_type": 3.0,
    "mined_name_attrs": 2.5,
    "color": 2.0,
    "aliases": 2.0,
    "category": 1.5,
    "pattern": 1.5,
    "audience": 1.5,
    "mined_desc_attrs": 1.5,
    "section": 1.0,
    "desc_keywords": 0.8
}


class PrecomputedIndex:
    def __init__(
        self,
        ids: list[str],
        columnar_arrays: dict[str, np.ndarray],
        cat_mappings: dict[str, dict[str, int]],
        presorted_orders: dict[str, np.ndarray],
        inverted_index: dict[str, list[tuple[int, float]]],
        phrase_index: dict[str, list[int]],
        doc_lengths: np.ndarray,
        avg_doc_len: float,
        price_percentiles: dict[str, dict[str, float]],
        metadata: dict
    ):
        self.ids = ids
        self.id_to_idx = {pid: i for i, pid in enumerate(ids)}
        self.arrays = columnar_arrays
        self.cat_mappings = cat_mappings
        self.presorted = presorted_orders
        self.inverted = inverted_index
        self.phrase_index = phrase_index
        self.doc_lengths = doc_lengths
        self.avg_doc_len = avg_doc_len
        self.price_percentiles = price_percentiles
        self.metadata = metadata

    def filter_mask(self, filters: dict) -> np.ndarray:
        """Fast vectorized boolean mask calculation for explicit filters (under 2 ms)."""
        n = len(self.ids)
        mask = np.ones(n, dtype=bool)

        if not filters:
            return mask

        # Price bounds
        if "min_price" in filters:
            mask &= (self.arrays["price"] >= filters["min_price"])
        if "max_price" in filters:
            mask &= (self.arrays["price"] <= filters["max_price"])

        # Rating bounds (null ratings fail min_rating)
        if "min_rating" in filters:
            rating_arr = self.arrays["rating"]
            mask &= (~np.isnan(rating_arr)) & (rating_arr >= filters["min_rating"])

        # Review count bounds
        if "min_review_count" in filters:
            mask &= (self.arrays["review_count"] >= filters["min_review_count"])

        # String filters (case-insensitive exact match)
        for key in ("category", "product_type", "audience", "section", "color", "pattern"):
            if key in filters:
                val = filters[key].strip().casefold()
                mapping = self.cat_mappings.get(key, {})
                code = mapping.get(val, -1)
                if code == -1:
                    # Unknown filter value matches 0 products
                    return np.zeros(n, dtype=bool)
                mask &= (self.arrays[key] == code)

        return mask

    def score_bm25(self, query_tokens: tuple[str, ...], candidate_indices: np.ndarray | None = None) -> np.ndarray:
        """Score candidate documents using BM25F."""
        n = len(self.ids)
        scores = np.zeros(n, dtype=np.float32)

        k1 = 1.2
        b = 0.75

        for tok in query_tokens:
            postings = self.inverted.get(tok)
            if not postings:
                continue

            df = len(postings)
            # IDF with smoothing
            idf = math.log(1.0 + (n - df + 0.5) / (df + 0.5))
            if idf <= 0:
                idf = 0.01

            for doc_idx, tf in postings:
                dl = self.doc_lengths[doc_idx]
                tf_norm = tf / (1.0 - b + b * (dl / self.avg_doc_len))
                score = idf * ((tf_norm * (k1 + 1.0)) / (tf_norm + k1))
                scores[doc_idx] += score

        return scores


def build_precomputed_index(products: list[dict], catalog_sha256: str) -> PrecomputedIndex:
    """Build complete deterministic search index from catalog records."""
    # Ensure ascending lexicographical order by ID
    sorted_prods = sorted(products, key=lambda p: str(p.get("id") or ""))
    n = len(sorted_prods)
    ids = [p["id"] for p in sorted_prods]

    # Categorical dictionaries
    cat_keys = ("category", "product_type", "audience", "section", "color", "pattern", "base_color")
    cat_mappings = {}
    for k in cat_keys:
        unique_vals = sorted(list(set(
            get_base_color(p.get("color") or "").casefold() if k == "base_color"
            else str(p.get(k) or "").strip().casefold()
            for p in sorted_prods
        )))
        cat_mappings[k] = {v: i for i, v in enumerate(unique_vals)}

    # Build columnar numpy arrays
    price_arr = np.array([float(p["price"]["amount"]) for p in sorted_prods], dtype=np.float32)
    rating_arr = np.array([
        float(p["rating"]["average"]) if p["rating"]["average"] is not None else np.nan
        for p in sorted_prods
    ], dtype=np.float32)
    review_count_arr = np.array([int(p["rating"]["count"]) for p in sorted_prods], dtype=np.int32)

    cat_arrays = {}
    for k in ("category", "product_type", "audience", "section", "color", "pattern"):
        mapping = cat_mappings[k]
        cat_arrays[k] = np.array([
            mapping[str(p.get(k) or "").strip().casefold()]
            for p in sorted_prods
        ], dtype=np.int16)
    base_color_mapping = cat_mappings["base_color"]
    cat_arrays["base_color"] = np.array([
        base_color_mapping[get_base_color(p.get("color") or "").casefold()]
        for p in sorted_prods
    ], dtype=np.int16)

    columnar_arrays = {
        "price": price_arr,
        "rating": rating_arr,
        "review_count": review_count_arr,
        **cat_arrays
    }

    # Presorted orders with ascending ID tie-break
    id_indices = np.arange(n, dtype=np.int32)

    # Price
    price_asc = np.lexsort((id_indices, price_arr))
    price_desc = np.lexsort((id_indices, -price_arr))

    # Review count
    rc_asc = np.lexsort((id_indices, review_count_arr))
    rc_desc = np.lexsort((id_indices, -review_count_arr))

    # Rating: null ratings always last for BOTH asc and desc
    is_unrated = np.isnan(rating_arr)
    rated_indices = np.where(~is_unrated)[0]
    unrated_indices = np.where(is_unrated)[0]

    # Rated sorted asc/desc with id tie-break
    rated_ratings = rating_arr[rated_indices]
    rated_id_idx = id_indices[rated_indices]
    rated_asc = rated_indices[np.lexsort((rated_id_idx, rated_ratings))]
    rated_desc = rated_indices[np.lexsort((rated_id_idx, -rated_ratings))]

    # Unrated in ascending id order
    unrated_sorted = unrated_indices[np.argsort(id_indices[unrated_indices])]

    rating_asc = np.concatenate([rated_asc, unrated_sorted])
    rating_desc = np.concatenate([rated_desc, unrated_sorted])

    presorted_orders = {
        "id_asc": id_indices,
        "id_desc": id_indices[::-1].copy(),
        "price_asc": price_asc,
        "price_desc": price_desc,
        "rating_asc": rating_asc,
        "rating_desc": rating_desc,
        "review_count_asc": rc_asc,
        "review_count_desc": rc_desc
    }

    # Inverted BM25F index & phrase bigrams
    inverted_index = collections.defaultdict(list)
    phrase_index = collections.defaultdict(list)
    doc_lengths = np.zeros(n, dtype=np.float32)

    # Compute price percentiles by product_type
    price_by_type = collections.defaultdict(list)
    for p in sorted_prods:
        pt = p.get("product_type") or "Unknown"
        price_by_type[pt].append(float(p["price"]["amount"]))

    price_percentiles = {}
    for pt, pr_list in price_by_type.items():
        pr_arr = np.array(sorted(pr_list))
        price_percentiles[pt] = {
            "p25": float(np.percentile(pr_arr, 25)),
            "p50": float(np.percentile(pr_arr, 50)),
            "p75": float(np.percentile(pr_arr, 75))
        }

    if n > 1000:
        print("Building BM25F inverted index and mined attributes...")
    for doc_idx, p in enumerate(sorted_prods):
        name = p.get("name") or ""
        desc = p.get("description") or ""
        ptype = p.get("product_type") or ""
        cat = p.get("category") or ""
        col = p.get("color") or ""
        pat = p.get("pattern") or ""
        aud = p.get("audience") or ""
        sec = p.get("section") or ""

        # Mined attributes
        mined = mine_attributes(name, desc)
        mined_name_words = []
        for term_list in mined["name_attrs"].values():
            mined_name_words.extend(term_list)
        mined_desc_words = []
        for term_list in mined["desc_attrs"].values():
            mined_desc_words.extend(term_list)

        # Tokenize fields
        field_tokens = {
            "name": tokenize_and_stem(name),
            "product_type": tokenize_and_stem(ptype),
            "category": tokenize_and_stem(cat),
            "color": tokenize_and_stem(col),
            "pattern": tokenize_and_stem(pat),
            "audience": tokenize_and_stem(aud),
            "section": tokenize_and_stem(sec),
            "mined_name_attrs": tokenize_and_stem(" ".join(mined_name_words)),
            "mined_desc_attrs": tokenize_and_stem(" ".join(mined_desc_words)),
            "desc_keywords": tokenize_and_stem(desc),
            "aliases": tokenize_and_stem(f"{PRODUCT_TYPE_ALIASES.get(ptype.lower(), '')} {CATEGORY_ALIASES.get(cat.lower(), '')}")
        }

        # Accumulate weighted term frequencies
        doc_tf = collections.defaultdict(float)
        total_len = 0.0
        for f_name, tokens in field_tokens.items():
            w = FIELD_WEIGHTS.get(f_name, 1.0)
            for tok in tokens:
                doc_tf[tok] += w
                total_len += w

        doc_lengths[doc_idx] = total_len
        for tok, tf in doc_tf.items():
            inverted_index[tok].append((doc_idx, tf))

        # Bigram phrase indexing from name and product type
        clean_name_tokens = list(tokenize_and_stem(f"{name} {ptype}"))
        for i in range(len(clean_name_tokens) - 1):
            bg = f"{clean_name_tokens[i]} {clean_name_tokens[i+1]}"
            phrase_index[bg].append(doc_idx)

    avg_doc_len = float(np.mean(doc_lengths))

    metadata = {
        "catalog_sha256": catalog_sha256,
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_products": n,
        "library_versions": {
            "numpy": np.__version__
        }
    }

    return PrecomputedIndex(
        ids=ids,
        columnar_arrays=columnar_arrays,
        cat_mappings=cat_mappings,
        presorted_orders=presorted_orders,
        inverted_index=dict(inverted_index),
        phrase_index=dict(phrase_index),
        doc_lengths=doc_lengths,
        avg_doc_len=avg_doc_len,
        price_percentiles=price_percentiles,
        metadata=metadata
    )


def save_precomputed_index(index: PrecomputedIndex, index_dir: Path):
    """Save index to disk deterministically."""
    index_dir.mkdir(parents=True, exist_ok=True)

    # Save columnar arrays and presorted orders in .npz
    np.savez_compressed(
        index_dir / "columnar.npz",
        **index.arrays,
        **index.presorted,
        doc_lengths=index.doc_lengths
    )

    # Save index payload with pickle
    payload = {
        "ids": index.ids,
        "cat_mappings": index.cat_mappings,
        "inverted": index.inverted,
        "phrase_index": index.phrase_index,
        "avg_doc_len": index.avg_doc_len,
        "price_percentiles": index.price_percentiles,
        "metadata": index.metadata
    }
    with open(index_dir / "index_data.pkl", "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    with open(index_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(index.metadata, f, indent=2)

    print(f"Index successfully saved to {index_dir}")


def load_precomputed_index(index_dir: Path) -> PrecomputedIndex:
    """Fast startup loader for prebuilt search index."""
    with open(index_dir / "metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)

    with open(index_dir / "index_data.pkl", "rb") as f:
        payload = pickle.load(f)

    npz = np.load(index_dir / "columnar.npz")
    columnar_keys = ["price", "rating", "review_count", "category", "product_type", "audience", "section", "color", "pattern", "base_color"]
    columnar_arrays = {k: npz[k] for k in columnar_keys}

    presorted_keys = ["id_asc", "id_desc", "price_asc", "price_desc", "rating_asc", "rating_desc", "review_count_asc", "review_count_desc"]
    presorted_orders = {k: npz[k] for k in presorted_keys}
    doc_lengths = npz["doc_lengths"]

    return PrecomputedIndex(
        ids=payload["ids"],
        columnar_arrays=columnar_arrays,
        cat_mappings=payload["cat_mappings"],
        presorted_orders=presorted_orders,
        inverted_index=payload["inverted"],
        phrase_index=payload["phrase_index"],
        doc_lengths=doc_lengths,
        avg_doc_len=payload["avg_doc_len"],
        price_percentiles=payload["price_percentiles"],
        metadata=metadata
    )
