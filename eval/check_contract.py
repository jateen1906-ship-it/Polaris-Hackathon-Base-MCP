#!/usr/bin/env python3
"""Contract and invariant tester for Polaris Catalog search.

Verifies:
1. Every returned ID is unique and exists in the catalog.
2. Filters are strictly respected (product_type, category, color, audience, min_price, max_price, min_rating, min_review_count).
3. Presorted ordering is mathematically correct with ascending-ID tie-breaking and null ratings strictly last.
4. Pagination consistency: page [offset:offset+limit] strictly equals that slice of a larger prefix (up to 100).
5. Recommendations rules:
   - Only returned when include_recommendations=True and results exist.
   - IDs are unique, valid, not in primary results.
   - for_product_id belongs to the returned page.
   - complement items are from different type families (no substitutes).
   - reason is <= 300 characters.
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from search import Catalog, STRING_FILTERS
from seo.taxonomy import PRODUCT_TYPE_TO_FAMILIES


def run_contract_checks(cat: Catalog, num_trials: int = 100):
    print(f"Running {num_trials} randomized contract checks on catalog ({len(cat.products)} items)...")
    
    products = cat.products
    all_ids = {p["id"] for p in products}
    assert len(all_ids) == len(products), "Catalog has duplicate product IDs!"

    categories = list({p["category"] for p in products if p.get("category")})
    product_types = list({p["product_type"] for p in products if p.get("product_type")})
    colors = list({p["color"] for p in products if p.get("color")})
    audiences = list({p["audience"] for p in products if p.get("audience")})

    sort_options = [
        {"field": "price", "direction": "asc"},
        {"field": "price", "direction": "desc"},
        {"field": "rating", "direction": "asc"},
        {"field": "rating", "direction": "desc"},
        {"field": "review_count", "direction": "asc"},
        {"field": "review_count", "direction": "desc"},
        {"field": "id", "direction": "asc"},
        {"field": "id", "direction": "desc"},
    ]

    passed = 0
    errors = []

    for trial in range(1, num_trials + 1):
        # Generate random arguments
        query = random.choice([
            None, "", "cotton", "black dress", "running shoes", "linen shirt",
            "casual summer top", "denim jeans", "winter jacket", "gold earrings"
        ])
        
        filters = {}
        if random.random() < 0.4:
            filters["category"] = random.choice(categories)
        if random.random() < 0.3:
            filters["product_type"] = random.choice(product_types)
        if random.random() < 0.3:
            filters["color"] = random.choice(colors)
        if random.random() < 0.2:
            filters["audience"] = random.choice(audiences)
        if random.random() < 0.2:
            filters["min_price"] = random.randint(100, 2000)
        if random.random() < 0.2:
            filters["max_price"] = random.randint(2000, 10000)
            if "min_price" in filters and filters["min_price"] > filters["max_price"]:
                filters["max_price"], filters["min_price"] = filters["min_price"], filters["max_price"]
        if random.random() < 0.2:
            filters["min_rating"] = round(random.uniform(2.5, 4.8), 1)
        if random.random() < 0.2:
            filters["min_review_count"] = random.randint(1, 50)

        sort = random.choice(sort_options) if random.random() < 0.7 else None
        include_recs = random.random() < 0.5
        limit = random.choice([5, 10, 20, 50])
        offset = random.choice([0, 5, 10])

        args = {
            "limit": limit,
            "offset": offset,
            "include_recommendations": include_recs,
        }
        if query:
            args["query"] = query
        if filters:
            args["filters"] = filters
        if sort:
            args["sort_by"] = sort["field"]
            args["sort_order"] = sort["direction"]

        try:
            res = cat.search(args)
            items = [cat.products[cat.engine.index.id_to_idx[r["id"]]] for r in res.get("results", [])]
            item_ids = [r["id"] for r in res.get("results", [])]

            # Invariant 1: Uniqueness and existence
            if len(item_ids) != len(set(item_ids)):
                raise AssertionError(f"Duplicate IDs returned: {item_ids}")
            for it_id in item_ids:
                if it_id not in all_ids:
                    raise AssertionError(f"Unknown ID {it_id} returned!")

            # Invariant 2: Filters strictly respected
            for it in items:
                for k, v in filters.items():
                    if k in STRING_FILTERS:
                        actual = it.get(k)
                        if actual != v:
                            raise AssertionError(f"Filter mismatch on {k}: expected {v}, got {actual}")
                    elif k == "min_price":
                        if it["price"]["amount"] < v:
                            raise AssertionError(f"Price {it['price']['amount']} < min_price {v}")
                    elif k == "max_price":
                        if it["price"]["amount"] > v:
                            raise AssertionError(f"Price {it['price']['amount']} > max_price {v}")
                    elif k == "min_rating":
                        if it.get("rating") is None or it["rating"].get("average") is None or it["rating"]["average"] < v:
                            raise AssertionError(f"Rating {it.get('rating')} < min_rating {v}")
                    elif k == "min_review_count":
                        if it.get("rating") is None or it["rating"].get("count", 0) < v:
                            raise AssertionError(f"Review count {it.get('rating')} < min_review_count {v}")

            # Invariant 3: Sort order consistency
            if sort and len(items) > 1:
                field = sort["field"]
                desc = (sort["direction"] == "desc")
                for i in range(len(items) - 1):
                    a = items[i]
                    b = items[i + 1]
                    if field == "price":
                        val_a = a["price"]["amount"]
                        val_b = b["price"]["amount"]
                    elif field == "rating":
                        val_a = a["rating"]["average"]
                        val_b = b["rating"]["average"]
                    elif field == "review_count":
                        val_a = a["rating"]["count"]
                        val_b = b["rating"]["count"]
                    else:
                        val_a = a["id"]
                        val_b = b["id"]

                    if field == "rating":
                        # Null ratings must be strictly last
                        if val_a is None and val_b is not None:
                            raise AssertionError(f"Null rating appeared before non-null: pos {i} vs {i+1}")
                        if val_a is not None and val_b is None:
                            continue # valid: non-null before null
                        if val_a is None and val_b is None:
                            # Both null: tie-break by ascending ID
                            if a["id"] >= b["id"]:
                                raise AssertionError(f"Ascending ID tie-break violated for null ratings: {a['id']} >= {b['id']}")
                            continue
                    
                    # Both non-null
                    if val_a == val_b:
                        # Tie break by ascending ID
                        if a["id"] >= b["id"]:
                            raise AssertionError(f"Ascending ID tie-break violated: {a['id']} >= {b['id']}")
                    elif desc:
                        if val_a < val_b:
                            raise AssertionError(f"Desc sort violated on {field}: {val_a} < {val_b}")
                    else:
                        if val_a > val_b:
                            raise AssertionError(f"Asc sort violated on {field}: {val_a} > {val_b}")

            # Invariant 4: Pagination consistency
            # Querying [offset:offset+limit] must match slice [offset:offset+limit] of [0:offset+limit]
            if items and (offset > 0 or limit < 50):
                prefix_limit = min(offset + limit, 100)
                prefix_args = dict(args)
                prefix_args["offset"] = 0
                prefix_args["limit"] = prefix_limit
                prefix_args["include_recommendations"] = False
                prefix_res = cat.search(prefix_args)
                prefix_items = prefix_res.get("results", [])
                expected_slice = prefix_items[offset:offset + limit]
                expected_ids = [it["id"] for it in expected_slice]
                if item_ids != expected_ids:
                    raise AssertionError(
                        f"Pagination slice mismatch: got {item_ids[:3]}... expected {expected_ids[:3]}..."
                    )

            # Invariant 5: Recommendations rules
            recs = res.get("recommendations", [])
            if not include_recs:
                if recs:
                    raise AssertionError("Recommendations returned when include_recommendations=False")
            elif not items:
                if recs:
                    raise AssertionError("Recommendations returned when items are empty")
            else:
                rec_ids = [r["id"] for r in recs]
                if len(rec_ids) != len(set(rec_ids)):
                    raise AssertionError("Duplicate recommendation IDs")
                for r in recs:
                    if r["id"] not in all_ids:
                        raise AssertionError(f"Unknown rec ID {r['id']}")
                    if r["id"] in item_ids:
                        raise AssertionError(f"Rec ID {r['id']} was in primary results!")
                    if r["for_product_id"] not in item_ids:
                        raise AssertionError(f"for_product_id {r['for_product_id']} not in page items")
                    if len(r.get("reason", "")) > 300:
                        raise AssertionError(f"Recommendation reason too long: {len(r.get('reason'))}")
                    
                    # Complement check: should not be same type family
                    primary_prod = next(it for it in items if it["id"] == r["for_product_id"])
                    rec_prod = cat.products[cat.engine.index.id_to_idx[r["id"]]]
                    primary_fams = set(PRODUCT_TYPE_TO_FAMILIES.get(primary_prod.get("product_type"), []))
                    rec_fams = set(PRODUCT_TYPE_TO_FAMILIES.get(rec_prod.get("product_type"), []))
                    common = primary_fams.intersection(rec_fams)
                    if common:
                        raise AssertionError(f"Recommendation {rec_prod.get('product_type')} shares family {common} with primary {primary_prod.get('product_type')} (substitute, not complement)!")

            passed += 1

        except Exception as e:
            errors.append(f"Trial {trial} failed with args {args}: {e}")
            if len(errors) >= 5:
                break

    print(f"\n--- Contract Check Results ---")
    print(f"Total Trials: {trial}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(errors)}")
    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"- {err}")
        return False
    else:
        print("ALL CONTRACT INVARIANTS SATISFIED 100%!")
        return True


if __name__ == "__main__":
    catalog = Catalog.load("data/products.json")
    success = run_contract_checks(catalog, num_trials=100)
    sys.exit(0 if success else 1)
