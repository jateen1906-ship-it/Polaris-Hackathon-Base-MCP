#!/usr/bin/env python3
"""Comprehensive evaluation suite for Polaris Product Search MCP.
Computes nDCG@10, choice coverage, empty accuracy, and recommendation scores.
Matches hackathon-brief.md scoring formulas.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from search import Catalog
from seo.taxonomy import PRODUCT_TYPE_TO_FAMILIES
from seo.colors import COLOR_TO_BASE, get_base_color

# Ideal DCG@10 with ten grade-3 reference slots (brief formula)
IDCG_10 = sum((2**3 - 1) / math.log2(i + 1) for i in range(1, 11))
IDCG_5 = sum((2**3 - 1) / math.log2(i + 1) for i in range(1, 6))


def grade_product(product: dict, query_spec: dict) -> int:
    """Grade product relevance from 0 to 3 based on catalog facts and query spec."""
    ptype = product.get("product_type") or ""
    cat = product.get("category") or ""
    color = product.get("color") or ""
    price = product["price"]["amount"]

    # Hard constraint check: price
    if "max_price" in query_spec and price > query_spec["max_price"]:
        return 0
    if "min_price" in query_spec and price < query_spec["min_price"]:
        return 0

    # Hard constraint check: color
    if query_spec.get("expected_colors"):
        req_colors = query_spec["expected_colors"]
        if color not in req_colors:
            # Check family
            if get_base_color(color) not in [get_base_color(rc) for rc in req_colors]:
                return 0

    # Direct relevance (Grade 3)
    if query_spec.get("expected_types") and ptype in query_spec["expected_types"]:
        return 3

    # Useful connection (Grade 2)
    if query_spec.get("expected_categories") and cat in query_spec["expected_categories"]:
        return 2

    # Concept match (Grade 2 or 3)
    if "expected_concepts" in query_spec:
        fams = PRODUCT_TYPE_TO_FAMILIES.get(ptype, [])
        for c in query_spec["expected_concepts"]:
            if c in ("lazy", "sleep") and ("nightwear" in fams or "footwear" in fams):
                return 3
            if c in ("beach", "summer") and ("swimwear" in fams or "footwear" in fams or "dresses" in fams):
                return 3
            if c in ("gym", "workout") and ("tops" in fams or "bottoms" in fams or "footwear" in fams):
                return 3
            if c in ("party", "wedding") and ("dresses" in fams or "outerwear" in fams or "jewellery" in fams):
                return 3
            if c in ("winter",) and ("outerwear" in fams or "tops" in fams or "accessories" in fams):
                return 3
            if c in ("office", "work") and ("outerwear" in fams or "tops" in fams or "bottoms" in fams):
                return 3
        return 2

    # Weak connection (Grade 1)
    name = (product.get("name") or "").lower()
    q_words = query_spec.get("query", "").lower().split()
    if any(w in name for w in q_words if len(w) >= 4):
        return 1

    return 0


def dcg_at_k(grades: list[int], k: int = 10) -> float:
    score = 0.0
    for i, g in enumerate(grades[:k], start=1):
        if g > 0:
            score += (2**g - 1) / math.log2(i + 1)
    return score


def evaluate(catalog: Catalog, queries_path: Path, held_out_only: bool = False):
    queries = []
    with open(queries_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))

    if held_out_only:
        queries = [q for q in queries if q.get("held_out", False)]
        print(f"Running evaluation on {len(queries)} HELD-OUT queries only.")
    else:
        print(f"Running evaluation on all {len(queries)} queries.")

    cat_stats = collections.defaultdict(lambda: {
        "count": 0, "ndcg_sum": 0.0, "empty_correct": 0, "coverage_sum": 0.0, "rec_sum": 0.0
    })

    t0 = time.time()
    for q in queries:
        cat_name = q["category"]
        stats = cat_stats[cat_name]
        stats["count"] += 1

        args = {
            "query": q["query"],
            "filters": q.get("filters", {}),
            "limit": 10,
            "include_recommendations": q.get("include_recommendations", False)
        }

        res = catalog.search(args)
        results = res.get("results", [])
        recs = res.get("recommendations", [])

        # 1. Impossible / Empty queries
        if q.get("expected_empty", False):
            if len(results) == 0 and len(recs) == 0:
                stats["empty_correct"] += 1
            continue

        # 2. Mixed queries
        if cat_name == "mixed":
            choices = q.get("choices", [])
            choice_covered = [False] * len(choices)
            grades = []
            for item in results[:10]:
                p_idx = catalog.engine.index.id_to_idx.get(item["id"])
                p = catalog.products[p_idx]
                g = 0
                for c_i, ch in enumerate(choices):
                    from seo.engine import ParsedQueryIntent
                    parsed_ch = ParsedQueryIntent(ch, catalog.engine.corrector)
                    ch_spec = {
                        "query": ch,
                        "expected_types": parsed_ch.detected_types,
                        "expected_colors": parsed_ch.detected_colors,
                        **parsed_ch.prose_constraints
                    }
                    ch_g = grade_product(p, ch_spec)
                    if ch_g >= 2:
                        choice_covered[c_i] = True
                    g = max(g, ch_g)
                grades.append(g)

            coverage = sum(choice_covered) / len(choices) if choices else 1.0
            ndcg = dcg_at_k(grades, 10) / IDCG_10
            stats["coverage_sum"] += coverage
            stats["ndcg_sum"] += ndcg
            continue

        # 3. Complements
        if cat_name == "complements":
            prim_grades = []
            for item in results[:10]:
                p_idx = catalog.engine.index.id_to_idx.get(item["id"])
                p = catalog.products[p_idx]
                prim_grades.append(grade_product(p, {"query": q["query"], "expected_types": [q.get("primary_type")]}))
            prim_ndcg = dcg_at_k(prim_grades, 10) / IDCG_10

            rec_grades = []
            for r in recs[:5]:
                r_idx = catalog.engine.index.id_to_idx.get(r["id"])
                r_prod = catalog.products[r_idx]
                rg = 3 if r_prod.get("product_type") == q.get("complement_type") else 1
                rec_grades.append(rg)
            rec_ndcg = dcg_at_k(rec_grades, 5) / IDCG_5 if recs else 0.0

            stats["rec_sum"] += (0.5 * prim_ndcg + 0.5 * rec_ndcg)
            continue

        # 4. Standard Ranking / Synonyms / Typos / Prose / Unusual
        grades = []
        for item in results[:10]:
            p_idx = catalog.engine.index.id_to_idx.get(item["id"])
            p = catalog.products[p_idx]
            grades.append(grade_product(p, q))

        ndcg = dcg_at_k(grades, 10) / IDCG_10
        stats["ndcg_sum"] += ndcg

    elapsed = time.time() - t0
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS REPORT")
    print("=" * 80)
    print(f"Total Queries Evaluated: {len(queries)} in {elapsed:.2f}s ({len(queries)/elapsed:.1f} qps)\n")

    print(f"{'Category':<22} | {'Count':<6} | {'nDCG@10':<9} | {'Special Metric':<25}")
    print("-" * 70)

    total_weighted_points = 0.0

    for cat_name, s in sorted(cat_stats.items()):
        cnt = s["count"]
        if cnt == 0:
            continue

        if cat_name == "impossible":
            acc = (s["empty_correct"] / cnt) * 100
            print(f"{cat_name:<22} | {cnt:<6} | {'N/A':<9} | Empty Accuracy: {acc:.1f}%")
            total_weighted_points += 7.5 * (s["empty_correct"] / cnt)
        elif cat_name == "mixed":
            cov = (s["coverage_sum"] / cnt) * 100
            ndcg = s["ndcg_sum"] / cnt
            mixed_score = 0.5 * (s["coverage_sum"] / cnt) + 0.5 * ndcg
            print(f"{cat_name:<22} | {cnt:<6} | {ndcg:<9.4f} | Coverage: {cov:.1f}% (Score: {mixed_score*15:.2f}/15)")
            total_weighted_points += 15.0 * mixed_score
        elif cat_name == "complements":
            rec_score = s["rec_sum"] / cnt
            print(f"{cat_name:<22} | {cnt:<6} | {'N/A':<9} | Rec Score: {rec_score*10:.2f}/10")
            total_weighted_points += 10.0 * rec_score
        else:
            ndcg = s["ndcg_sum"] / cnt
            print(f"{cat_name:<22} | {cnt:<6} | {ndcg:<9.4f} | Mean nDCG: {ndcg*100:.1f}%")
            if cat_name in ("single_intent", "synonyms", "typos", "prose_constraints"):
                total_weighted_points += (30.0 / 4) * ndcg
            elif cat_name == "unusual":
                total_weighted_points += 7.5 * ndcg

    print("-" * 70)
    print(f"Estimated Functional Ranking Points (out of 70 points): {total_weighted_points:.2f} / 70.00")
    print("=" * 80)
    return total_weighted_points


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--held-out-only", action="store_true")
    parser.add_argument("--queries", default=str(ROOT / "eval" / "queries.jsonl"))
    args = parser.parse_args()

    cat = Catalog.load(ROOT / "data" / "products.json")
    evaluate(cat, Path(args.queries), held_out_only=args.held_out_only)
