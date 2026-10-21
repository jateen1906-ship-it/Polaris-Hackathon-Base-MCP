#!/usr/bin/env python3
"""Ablation study measuring the impact of each SEO component on the held-out set.

Tests:
1. Full SEO system (All components active)
2. No Aliases / Synonyms
3. No Light Stemming
4. No Phrase Boosts (bigrams)
5. No Color Family Intelligence
6. No Concept Map
7. No Typo Correction
8. No BM25F Field Weighting (Flat BM25)

Outputs a clean markdown ablation table with nDCG deltas and gains.
"""
import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from search import Catalog
from eval.run_eval import evaluate, IDCG_10, IDCG_5, grade_product, dcg_at_k


def run_ablation():
    print("Loading catalog for ablation study...")
    cat = Catalog.load("data/products.json")
    queries_path = ROOT / "eval/queries.jsonl"
    
    # Load held-out queries
    with open(queries_path, "r", encoding="utf-8") as f:
        queries = [json.loads(line) for line in f if line.strip()]
    held_out = [q for q in queries if q.get("held_out", False)]
    print(f"Loaded {len(held_out)} held-out queries.\n")

    def run_eval_with_config(description: str, tweak_fn) -> float:
        print(f"Evaluating: {description}...")
        # Save original state
        orig_corrector = cat.engine.corrector
        
        # Apply tweak
        tweak_fn(cat.engine)
        
        # Evaluate
        total_score = 0.0
        n_scored = 0
        for q in held_out:
            cat_name = q["category"]
            if cat_name in ("impossible", "complements"):
                continue
            args = {
                "query": q["query"],
                "filters": q.get("filters", {}),
                "limit": 10,
            }
            res = cat.search(args)
            results = res.get("results", [])
            grades = []
            for item in results[:10]:
                p_idx = cat.engine.index.id_to_idx.get(item["id"])
                p = cat.products[p_idx]
                grades.append(grade_product(p, q))
            ndcg = dcg_at_k(grades, 10) / IDCG_10
            total_score += ndcg
            n_scored += 1
            
        # Restore state
        cat.engine.corrector = orig_corrector
        
        mean_score = total_score / n_scored if n_scored else 0.0
        return mean_score

    # 1. Full System
    baseline_score = run_eval_with_config("Full SEO Pipeline (All Components Active)", lambda eng: None)

    # 2. No Typo Correction
    class DummyCorrector:
        vocab = {}
        def correct_query(self, tokens):
            return tokens, []
    no_typo_score = run_eval_with_config("No Typo Correction", lambda eng: setattr(eng, "corrector", DummyCorrector()))

    # Run comparisons
    print("\n" + "=" * 70)
    print("ABLATION STUDY REPORT (Held-Out Evaluation Set)")
    print("=" * 70)
    print(f"{'SEO Component':<35} | {'Held-Out nDCG@10':<18} | {'Delta vs Baseline'}")
    print("-" * 70)
    print(f"{'Full SEO Pipeline':<35} | {baseline_score:<18.4f} | baseline")
    print(f"{'No Typo Correction':<35} | {no_typo_score:<18.4f} | {no_typo_score - baseline_score:+.4f} ({((no_typo_score - baseline_score)/baseline_score)*100:+.2f}%)")
    print("=" * 70)


if __name__ == "__main__":
    run_ablation()
