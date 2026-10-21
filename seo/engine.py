"""Search engine query interpretation, candidate retrieval, ranking, and recommendations."""
import collections
import json
import math
import re
from pathlib import Path
import numpy as np

from seo.normalize import normalize_text, tokenize_and_stem, light_stem, extract_price_constraints
from seo.taxonomy import PRODUCT_TYPE_TO_FAMILIES
from seo.colors import COLOR_TO_BASE, get_base_color, color_matches
from seo.complements import get_complementary_product_types
from seo.concepts import get_concept, CONCEPT_MAP
from seo.spelling import SpellingCorrector, NON_FASHION_WORDS
from seo.mining import ALL_ATTRIBUTES
from seo.aliases import (
    PRODUCT_TYPE_ALIASES, CATEGORY_ALIASES, AUDIENCE_ALIASES,
    COLOR_ALIASES, PATTERN_ALIASES
)
from seo.indexer import PrecomputedIndex, build_precomputed_index, load_precomputed_index

# Build global set of known fashion terms across all taxonomies
ALL_FASHION_TERMS = set()
for d in (PRODUCT_TYPE_ALIASES, CATEGORY_ALIASES, AUDIENCE_ALIASES, COLOR_ALIASES, PATTERN_ALIASES):
    for k in d:
        ALL_FASHION_TERMS.update(k.lower().split())
for terms in ALL_ATTRIBUTES.values():
    for t in terms:
        ALL_FASHION_TERMS.update(t.lower().split())
for c_data in CONCEPT_MAP.values():
    for kw in c_data.get("keywords", []):
        ALL_FASHION_TERMS.update(kw.lower().split())
for pt in PRODUCT_TYPE_TO_FAMILIES:
    ALL_FASHION_TERMS.update(pt.lower().split())

SHOPPING_FILLER = {
    "show", "me", "find", "looking", "for", "i", "want", "need", "can", "you",
    "please", "give", "search", "something", "anything", "some", "the", "a",
    "an", "in", "of", "to", "at", "on", "with", "buy", "get"
}

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours"
}


class ParsedQueryIntent:
    def __init__(self, raw_query: str, corrector: SpellingCorrector = None):
        self.raw_query = raw_query.strip()
        self.is_empty = not bool(self.raw_query)
        self.is_complement_query = False
        self.is_mixed_query = False
        self.primary_query = self.raw_query
        self.accessory_query = ""
        self.choices = []
        self.prose_constraints = {}
        self.accessory_constraints = {}
        self.tokens = ()
        self.detected_types = []
        self.detected_categories = []
        self.detected_colors = []
        self.detected_audience = None
        self.is_impossible = False

        if not self.is_empty:
            self._parse(corrector)

    def _parse(self, corrector: SpellingCorrector = None):
        norm = normalize_text(self.raw_query)

        # 1. Check for complementary requests
        m_comp = re.search(r'\b(?:with\s+a\s+matching|accompanied\s+by|paired\s+with|along\s+with|matching)\s+(.+)$', norm, flags=re.IGNORECASE)
        if m_comp:
            self.is_complement_query = True
            self.accessory_query = m_comp.group(1).strip()
            self.primary_query = norm[:m_comp.start()].strip()
            self.accessory_constraints = extract_price_constraints(self.accessory_query)
        else:
            # 2. Check for mixed queries
            if " and " in norm and not re.search(r'\b(black and white|socks and tights|underwear and nightwear)\b', norm):
                parts = norm.split(" and ", 1)
                c1, c2 = parts[0].strip(), parts[1].strip()
                if c1 and c2:
                    self.is_mixed_query = True
                    self.choices = [c1, c2]

        self.prose_constraints = extract_price_constraints(self.primary_query)

        # Tokenize and correct typos
        raw_tokens = list(tokenize_and_stem(self.primary_query))
        if corrector and corrector.vocab:
            corrected_tokens, _ = corrector.correct_query(raw_tokens)
            self.tokens = tuple(corrected_tokens)
        else:
            self.tokens = tuple(raw_tokens)

        meaningful = [t for t in self.tokens if t not in SHOPPING_FILLER and t not in STOPWORDS]

        # Attribute detection
        for tok in meaningful:
            if tok in PRODUCT_TYPE_ALIASES:
                pt = PRODUCT_TYPE_ALIASES[tok]
                if pt not in self.detected_types:
                    self.detected_types.append(pt)
            if tok in COLOR_ALIASES:
                col = COLOR_ALIASES[tok]
                if col not in self.detected_colors:
                    self.detected_colors.append(col)
            if tok in AUDIENCE_ALIASES and not self.detected_audience:
                self.detected_audience = AUDIENCE_ALIASES[tok]
            if tok in CATEGORY_ALIASES:
                cat = CATEGORY_ALIASES[tok]
                if cat not in self.detected_categories:
                    self.detected_categories.append(cat)

        for alias, target in PRODUCT_TYPE_ALIASES.items():
            if " " in alias and alias in self.primary_query:
                if target not in self.detected_types:
                    self.detected_types.append(target)
        for alias, target in COLOR_ALIASES.items():
            if " " in alias and alias in self.primary_query:
                if target not in self.detected_colors:
                    self.detected_colors.append(target)

        # Abstention: If query has explicit non-fashion / technical words
        raw_words = set(re.findall(r'[a-zA-Z]+', norm))
        if any(w in NON_FASHION_WORDS for w in raw_words):
            self.is_impossible = True


class SearchEngine:
    def __init__(self, products: list[dict], index_dir: Path | None = None):
        self.products = sorted(products, key=lambda p: str(p.get("id") or ""))
        self.n = len(self.products)
        min_freq = 5 if self.n >= 1000 else 1
        self.corrector = SpellingCorrector.from_products(self.products, min_freq=min_freq)

        self.index = None
        if index_dir and (index_dir / "metadata.json").exists() and self.n == 105126:
            try:
                self.index = load_precomputed_index(index_dir)
            except Exception as e:
                print(f"Warning: Failed to load precomputed index ({e}). Rebuilding...")

        if not self.index:
            self.index = build_precomputed_index(self.products, "in_memory_catalog")

    def search_candidates(self, parsed: ParsedQueryIntent, filters: dict, max_candidates: int = 1000) -> list[int]:
        """Retrieve and rank candidate product indices."""
        if parsed.is_impossible:
            return []

        mask = self.index.filter_mask(filters)

        # Apply hard constraints from prose if not overridden by explicit filters
        if "max_price" not in filters and "max_price" in parsed.prose_constraints:
            mask &= (self.index.arrays["price"] <= parsed.prose_constraints["max_price"])
        if "min_price" not in filters and "min_price" in parsed.prose_constraints:
            mask &= (self.index.arrays["price"] >= parsed.prose_constraints["min_price"])

        valid_indices = np.where(mask)[0]
        if len(valid_indices) == 0:
            return []

        tokens = [t for t in parsed.tokens if t not in SHOPPING_FILLER and t not in STOPWORDS]
        if not tokens:
            return list(valid_indices)

        scores = self.index.score_bm25(tuple(tokens))

        # Color boost from query text (strong signal, without hard-masking color words that appear in titles)
        for col in parsed.detected_colors:
            col_code = self.index.cat_mappings["color"].get(col.strip().casefold(), -1)
            if col_code != -1:
                scores += (self.index.arrays["color"] == col_code) * 10.0
            base = get_base_color(col).casefold()
            base_code = self.index.cat_mappings["base_color"].get(base, -1)
            if base_code != -1:
                scores += (self.index.arrays["base_color"] == base_code) * 5.0

        # Exact product name match boost:
        # Exact product name match boost:
        # If all query tokens appear in product name/tokens, give a strong match boost
        all_tokens_match = np.zeros(self.n, dtype=bool)
        if len(tokens) >= 1:
            match_counts = np.zeros(self.n, dtype=np.int16)
            for tok in tokens:
                for d_idx, _ in self.index.inverted.get(tok, []):
                    match_counts[d_idx] += 1
            all_tokens_match = (match_counts == len(tokens))
            scores += all_tokens_match * 25.0
            if len(tokens) >= 2:
                scores += (match_counts >= (len(tokens) - 1)) * 5.0

        # Check required tokens: If query has specific product type or head noun, enforce type/family relevance
        if parsed.detected_types:
            type_codes = set()
            allowed_family_codes = set()
            for pt in parsed.detected_types:
                code = self.index.cat_mappings["product_type"].get(pt.strip().casefold(), -1)
                if code != -1:
                    type_codes.add(code)
                for fam in PRODUCT_TYPE_TO_FAMILIES.get(pt, []):
                    for fam_pt, f_set in PRODUCT_TYPE_TO_FAMILIES.items():
                        if fam in f_set:
                            f_code = self.index.cat_mappings["product_type"].get(fam_pt.strip().casefold(), -1)
                            if f_code != -1:
                                allowed_family_codes.add(f_code)

            if type_codes:
                is_type = np.isin(self.index.arrays["product_type"], list(type_codes))
                matching_in_valid = np.intersect1d(valid_indices, np.where(is_type)[0])
                if len(matching_in_valid) == 0 and not np.any(all_tokens_match[valid_indices]):
                    # No product matches the hard constraints and requested product type
                    return []

                # Dominant boost for exact product type match
                scores += is_type * 35.0

                # Suppress products from incompatible type families unless name matches all query tokens
                if allowed_family_codes:
                    incompatible = ~np.isin(self.index.arrays["product_type"], list(allowed_family_codes))
                    scores[incompatible & ~all_tokens_match] = 0.0

        # Exact category boost
        for cat in parsed.detected_categories:
            code = self.index.cat_mappings["category"].get(cat.strip().casefold(), -1)
            if code != -1:
                is_cat = (self.index.arrays["category"] == code)
                scores += is_cat * 5.0

        # Phrase boosts from 2-grams
        for i in range(len(tokens) - 1):
            bg = f"{tokens[i]} {tokens[i+1]}"
            for doc_idx in self.index.phrase_index.get(bg, []):
                scores[doc_idx] += 4.0

        # Concept boosts
        for tok in tokens:
            concept = get_concept(tok)
            if concept:
                for pt in concept.get("product_types", []):
                    code = self.index.cat_mappings["product_type"].get(pt.strip().casefold(), -1)
                    if code != -1:
                        scores += (self.index.arrays["product_type"] == code) * 3.0

        candidate_scores = scores[valid_indices]
        positive_mask = candidate_scores > 0.05
        matched_indices = valid_indices[positive_mask]
        matched_scores = candidate_scores[positive_mask]

        if len(matched_indices) == 0:
            return []

        # Dynamic pruning: if top candidates match well, prune weak tail matches
        max_s = float(np.max(matched_scores))
        if max_s > 0.1 and len(tokens) >= 2:
            viable_mask = matched_scores >= (0.30 * max_s)
            matched_indices = matched_indices[viable_mask]
            matched_scores = matched_scores[viable_mask]

        id_order = self.index.presorted["id_asc"][matched_indices]
        sort_idx = np.lexsort((id_order, -matched_scores))

        ranked_indices = matched_indices[sort_idx][:max_candidates]
        return list(ranked_indices)

    def execute_search(self, arguments: dict) -> dict:
        """Main search entry point matching competition contract."""
        query_str = arguments.get("query", "").strip()
        filters = arguments.get("filters", {})
        sort_by = arguments.get("sort_by", "relevance")
        sort_order = arguments.get("sort_order", "desc")
        offset = arguments.get("offset", 0)
        limit = arguments.get("limit", 10)
        include_recommendations = arguments.get("include_recommendations", False)

        parsed = ParsedQueryIntent(query_str, self.corrector)

        if parsed.is_impossible:
            return {"results": [], "recommendations": []}

        # 1. Empty query fast path
        if parsed.is_empty:
            mask = self.index.filter_mask(filters)
            valid_indices = np.where(mask)[0]
            if len(valid_indices) == 0:
                return {"results": [], "recommendations": []}

            if sort_by == "relevance":
                order_key = "id_asc"
            else:
                order_key = f"{sort_by}_{sort_order}"

            full_order = self.index.presorted[order_key]
            ordered_candidates = [idx for idx in full_order if mask[idx]]
            sliced = ordered_candidates[offset:offset + limit]
            results = [{"id": self.products[idx]["id"]} for idx in sliced]
            return {
                "results": results,
                "recommendations": []
            }

        # 2. Mixed Query Handling
        if parsed.is_mixed_query:
            p1 = ParsedQueryIntent(parsed.choices[0], self.corrector)
            p2 = ParsedQueryIntent(parsed.choices[1], self.corrector)
            if "max_price" in parsed.prose_constraints:
                p1.prose_constraints.setdefault("max_price", parsed.prose_constraints["max_price"])
                p2.prose_constraints.setdefault("max_price", parsed.prose_constraints["max_price"])
            if "min_price" in parsed.prose_constraints:
                p1.prose_constraints.setdefault("min_price", parsed.prose_constraints["min_price"])
                p2.prose_constraints.setdefault("min_price", parsed.prose_constraints["min_price"])
            c1_indices = self.search_candidates(p1, filters, max_candidates=200)
            c2_indices = self.search_candidates(p2, filters, max_candidates=200)

            interleaved = []
            seen = set()
            max_len = max(len(c1_indices), len(c2_indices))
            for i in range(max_len):
                if i < len(c1_indices):
                    idx1 = c1_indices[i]
                    if idx1 not in seen:
                        interleaved.append(idx1)
                        seen.add(idx1)
                if i < len(c2_indices):
                    idx2 = c2_indices[i]
                    if idx2 not in seen:
                        interleaved.append(idx2)
                        seen.add(idx2)
            candidate_indices = interleaved
        else:
            candidate_indices = self.search_candidates(parsed, filters, max_candidates=1000)

        if not candidate_indices:
            return {"results": [], "recommendations": []}

        # 3. Field Sorting for Non-empty Queries
        if sort_by != "relevance":
            reverse = (sort_order == "desc")
            if sort_by == "price":
                candidate_indices.sort(key=lambda idx: (self.products[idx]["price"]["amount"] * (-1 if reverse else 1), self.products[idx]["id"]))
            elif sort_by == "rating":
                rated = [idx for idx in candidate_indices if self.products[idx]["rating"]["average"] is not None]
                unrated = [idx for idx in candidate_indices if self.products[idx]["rating"]["average"] is None]
                rated.sort(key=lambda idx: (self.products[idx]["rating"]["average"] * (-1 if reverse else 1), self.products[idx]["id"]))
                unrated.sort(key=lambda idx: self.products[idx]["id"])
                candidate_indices = rated + unrated
            elif sort_by == "review_count":
                candidate_indices.sort(key=lambda idx: (self.products[idx]["rating"]["count"] * (-1 if reverse else 1), self.products[idx]["id"]))
            elif sort_by == "id":
                candidate_indices.sort(key=lambda idx: self.products[idx]["id"], reverse=reverse)

        sliced = candidate_indices[offset:offset + limit]
        results = [{"id": self.products[idx]["id"]} for idx in sliced]

        # 4. Complementary Recommendations
        recommendations = []
        if include_recommendations and results:
            recommendations = self.generate_recommendations(results, sliced, parsed, filters)

        return {
            "results": results,
            "recommendations": recommendations
        }

    def generate_recommendations(
        self,
        results: list[dict],
        primary_indices: list[int],
        parsed: ParsedQueryIntent | None,
        primary_filters: dict
    ) -> list[dict]:
        """Generate up to 5 complementary accessories referencing primary products on this page."""
        primary_ids = set(r["id"] for r in results)
        rec_ids = set()
        recommendations = []

        rec_filters = {}
        if "audience" in primary_filters:
            rec_filters["audience"] = primary_filters["audience"]
        elif parsed and parsed.detected_audience:
            rec_filters["audience"] = parsed.detected_audience

        acc_max_price = parsed.accessory_constraints.get("max_price") if parsed else None
        if acc_max_price:
            rec_filters["max_price"] = acc_max_price

        req_comp_types = []
        if parsed and parsed.is_complement_query and parsed.accessory_query:
            acc_p = ParsedQueryIntent(parsed.accessory_query, self.corrector)
            req_comp_types = acc_p.detected_types

        # Round-robin spreading across primary products
        for round_idx in range(5):
            if len(recommendations) >= 5:
                break
            for p_idx in primary_indices:
                if len(recommendations) >= 5:
                    break
                primary = self.products[p_idx]
                primary_id = primary["id"]
                primary_type = primary.get("product_type") or "Unknown"

                comp_types = get_complementary_product_types(primary_type)
                if not comp_types:
                    continue

                if req_comp_types:
                    preferred = [t for t in req_comp_types if t in comp_types]
                    comp_types = preferred + [t for t in comp_types if t not in preferred]

                if round_idx < len(comp_types):
                    comp_type = comp_types[round_idx]
                    target_filters = dict(rec_filters)
                    target_filters["product_type"] = comp_type
                    mask = self.index.filter_mask(target_filters)
                    comp_indices = np.where(mask)[0]

                    for c_idx in comp_indices:
                        candidate = self.products[c_idx]
                        c_id = candidate["id"]
                        if c_id not in primary_ids and c_id not in rec_ids:
                            rec_ids.add(c_id)
                            c_name = candidate.get("name") or comp_type
                            reason = f"A complementary {comp_type} ({c_name}) to coordinate with the selected {primary_type}."
                            if len(reason) > 300:
                                reason = reason[:297] + "..."
                            recommendations.append({
                                "id": c_id,
                                "for_product_id": primary_id,
                                "reason": reason
                            })
                            break

        return recommendations
