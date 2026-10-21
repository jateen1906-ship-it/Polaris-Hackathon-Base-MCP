#!/usr/bin/env python3
"""Deep catalog profiler for Polaris Hackathon.
Analyzes data/products.json and generates docs/data_profile.md.
"""
import collections
import json
import math
import os
import re
import statistics
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_PATH = ROOT / "data" / "products.json"
DOCS_DIR = ROOT / "docs"
OUTPUT_MD = DOCS_DIR / "data_profile.md"
DERIVED_DIR = ROOT / "data_derived"


def percentile(data, p):
    if not data:
        return 0
    k = (len(data) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    d0 = data[int(f)] * (c - k)
    d1 = data[int(c)] * (k - f)
    return d0 + d1


def profile():
    print(f"Loading {PRODUCTS_PATH}...")
    with open(PRODUCTS_PATH, "r", encoding="utf-8") as f:
        products = json.load(f)
    n_products = len(products)
    print(f"Loaded {n_products} products.")

    # 1. Null / empty analysis
    fields = [
        "id", "name", "description", "category", "product_type",
        "audience", "section", "color", "pattern", "image_url",
        "price_amount", "rating_average", "rating_count", "reviews_count"
    ]
    null_counts = collections.defaultdict(int)
    empty_str_counts = collections.defaultdict(int)

    # 2. Categoricals
    cat_fields = ["product_type", "category", "audience", "section", "color", "pattern"]
    cat_counts = {k: collections.Counter() for k in cat_fields}
    cat_case_variants = {k: collections.defaultdict(set) for k in cat_fields}
    cat_whitespace = {k: set() for k in cat_fields}

    # 3. Names
    name_lengths = []
    name_word_counts = []
    name_tokens = collections.Counter()
    name_counter = collections.Counter()
    all_caps_names = 0
    title_case_names = 0
    lower_case_names = 0
    non_ascii_names = collections.Counter()
    digit_pattern_names = collections.Counter()
    punct_names = collections.Counter()

    # 4. Descriptions
    desc_lengths = []
    desc_word_counts = []
    desc_phrases = collections.Counter()

    # Attributes in text
    material_keywords = [
        "cotton", "polyester", "elastane", "viscose", "linen", "wool", "silk",
        "denim", "leather", "nylon", "fleece", "jersey", "chiffon", "satin",
        "velvet", "twill", "modal", "cashmere", "acrylic", "canvas", "suede",
        "flannel", "poplin", "jacquard", "lace", "mesh", "knit", "ribbed"
    ]
    fit_keywords = [
        "regular fit", "slim fit", "skinny fit", "relaxed fit", "loose fit",
        "oversized", "tight fit", "wide leg", "straight leg", "tapered",
        "flared", "bootcut", "boyfriend", "mom fit", "tailored"
    ]
    neck_keywords = [
        "round neck", "v-neck", "v neck", "crew neck", "boat neck", "halterneck",
        "turtleneck", "high neck", "hooded", "polo collar", "collared",
        "sweetheart neckline", "square neckline", "off-the-shoulder", "mandarin collar"
    ]
    sleeve_keywords = [
        "sleeveless", "short sleeve", "long sleeve", "3/4 sleeve", "cap sleeve",
        "drop shoulder", "puff sleeve", "raglan sleeve", "flutter sleeve"
    ]
    length_keywords = [
        "mini", "midi", "maxi", "cropped", "ankle length", "knee length",
        "calf length", "full length", "short", "long"
    ]
    closure_keywords = [
        "button", "zip", "zipper", "elasticated", "drawstring", "tie belt",
        "press stud", "hook-and-eye", "snap", "pull-on", "concealed zip"
    ]
    occasion_keywords = [
        "casual", "party", "wedding", "office", "formal", "work", "summer",
        "winter", "beach", "gym", "workout", "sport", "running", "yoga",
        "sleepwear", "lounge", "loungewear", "festive", "holiday", "outdoor"
    ]

    attr_name_mentions = collections.defaultdict(int)
    attr_desc_mentions = collections.defaultdict(int)

    # 5. Price & Rating
    prices = []
    ratings = []
    review_counts = []
    price_by_type = collections.defaultdict(list)

    # 6. Duplicates & Overlaps
    type_category_map = collections.defaultdict(set)
    type_audience_map = collections.defaultdict(set)
    type_section_map = collections.defaultdict(set)

    for p in products:
        pid = p.get("id")
        name = p.get("name")
        desc = p.get("description")
        category = p.get("category")
        ptype = p.get("product_type")
        audience = p.get("audience")
        section = p.get("section")
        color = p.get("color")
        pattern = p.get("pattern")
        img = p.get("image_url")
        price_dict = p.get("price") or {}
        price = price_dict.get("amount")
        rating_dict = p.get("rating") or {}
        rating_avg = rating_dict.get("average")
        rating_cnt = rating_dict.get("count", 0)
        reviews = p.get("reviews") or []

        # Null checks
        if pid is None: null_counts["id"] += 1
        if name is None: null_counts["name"] += 1
        if desc is None: null_counts["description"] += 1
        if category is None: null_counts["category"] += 1
        if ptype is None: null_counts["product_type"] += 1
        if audience is None: null_counts["audience"] += 1
        if section is None: null_counts["section"] += 1
        if color is None: null_counts["color"] += 1
        if pattern is None: null_counts["pattern"] += 1
        if img is None: null_counts["image_url"] += 1
        if price is None: null_counts["price_amount"] += 1
        if rating_avg is None: null_counts["rating_average"] += 1

        # Empty str checks
        for k, v in [("name", name), ("description", desc), ("category", category),
                     ("product_type", ptype), ("audience", audience), ("section", section),
                     ("color", color), ("pattern", pattern)]:
            if isinstance(v, str) and not v.strip():
                empty_str_counts[k] += 1

        # Categoricals
        for k, v in [("product_type", ptype), ("category", category),
                     ("audience", audience), ("section", section),
                     ("color", color), ("pattern", pattern)]:
            if v is not None:
                s_val = str(v)
                cat_counts[k][s_val] += 1
                cat_case_variants[k][s_val.strip().casefold()].add(s_val)
                if s_val != s_val.strip():
                    cat_whitespace[k].add(s_val)

        # Cross relations
        if ptype and category:
            type_category_map[ptype].add(category)
        if ptype and audience:
            type_audience_map[ptype].add(audience)
        if ptype and section:
            type_section_map[ptype].add(section)

        # Price & rating
        if price is not None:
            prices.append(price)
            if ptype:
                price_by_type[ptype].append(price)
        if rating_avg is not None:
            ratings.append(rating_avg)
        review_counts.append(rating_cnt)

        # Name analysis
        if name:
            name_counter[name] += 1
            name_lengths.append(len(name))
            tokens = re.findall(r"\w+", name.casefold())
            name_word_counts.append(len(tokens))
            for tok in tokens:
                name_tokens[tok] += 1

            if name.isupper():
                all_caps_names += 1
            elif name.istitle():
                title_case_names += 1
            elif name.islower():
                lower_case_names += 1

            for ch in name:
                if ord(ch) >= 128:
                    non_ascii_names[ch] += 1
                elif not ch.isalnum() and not ch.isspace():
                    punct_names[ch] += 1

            # Check digit patterns like 2-pack, 3pk, etc.
            pack_matches = re.findall(r"\b\d+[\s-]*(?:pack|pk|pck|prs?|pair|pieces?|pcs?)\b", name, re.IGNORECASE)
            for pm in pack_matches:
                digit_pattern_names[pm.lower()] += 1

            # Check attribute mentions in name
            name_lower = name.lower()
            for kw in material_keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", name_lower):
                    attr_name_mentions[kw] += 1
            for kw in fit_keywords:
                if kw in name_lower:
                    attr_name_mentions[kw] += 1
            for kw in neck_keywords:
                if kw in name_lower:
                    attr_name_mentions[kw] += 1
            for kw in sleeve_keywords:
                if kw in name_lower:
                    attr_name_mentions[kw] += 1
            for kw in length_keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", name_lower):
                    attr_name_mentions[kw] += 1
            for kw in occasion_keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", name_lower):
                    attr_name_mentions[kw] += 1

        # Description analysis
        if desc:
            desc_lengths.append(len(desc))
            desc_tokens = re.findall(r"\w+", desc.casefold())
            desc_word_counts.append(len(desc_tokens))
            desc_lower = desc.lower()

            # First sentence / boilerplate candidate
            sentences = desc.split(".")
            if sentences:
                first_sent = sentences[0].strip()
                if 10 < len(first_sent) < 80:
                    desc_phrases[first_sent] += 1

            for kw in material_keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", desc_lower):
                    attr_desc_mentions[kw] += 1
            for kw in fit_keywords:
                if kw in desc_lower:
                    attr_desc_mentions[kw] += 1
            for kw in neck_keywords:
                if kw in desc_lower:
                    attr_desc_mentions[kw] += 1
            for kw in sleeve_keywords:
                if kw in desc_lower:
                    attr_desc_mentions[kw] += 1
            for kw in length_keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", desc_lower):
                    attr_desc_mentions[kw] += 1
            for kw in closure_keywords:
                if kw in desc_lower:
                    attr_desc_mentions[kw] += 1
            for kw in occasion_keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", desc_lower):
                    attr_desc_mentions[kw] += 1

    prices.sort()
    ratings.sort()
    review_counts.sort()
    name_lengths.sort()
    desc_lengths.sort()

    # Identify potential abbreviations
    # Look for tokens of length <= 4 that appear frequently in names
    abbr_candidates = collections.Counter()
    for tok, cnt in name_tokens.most_common():
        if len(tok) <= 4 and cnt >= 50 and tok.isalpha():
            abbr_candidates[tok] = cnt

    # Generate Markdown profile
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Polaris Catalog Deep Data Profile\n\n")
        f.write("Generated by `scripts/profile_data.py`. Catalog: `data/products.json`.\n\n")
        f.write(f"- Total Products: **{n_products:,}**\n")
        f.write(f"- Catalog SHA-256: `05b6aa5e8e8c1c8c997d584f8288e432862454f8820531e13473443e83c8f073`\n\n")

        # 1. Null and Empty Rates
        f.write("## 1. Field-Level Completeness and Null Rates\n\n")
        f.write("| Field | Null Count | Null Rate (%) | Empty String Count |\n")
        f.write("| --- | ---: | ---: | ---: |\n")
        for field in fields:
            nc = null_counts[field]
            nr = (nc / n_products) * 100
            ec = empty_str_counts.get(field, 0)
            f.write(f"| `{field}` | {nc:,} | {nr:.2f}% | {ec:,} |\n")
        f.write("\n")

        # 2. Categorical Field Distributions
        f.write("## 2. Categorical Value Distributions and Integrity\n\n")
        for k in cat_fields:
            cntr = cat_counts[k]
            variants = {k2: v2 for k2, v2 in cat_case_variants[k].items() if len(v2) > 1}
            ws = cat_whitespace[k]
            f.write(f"### 2.{cat_fields.index(k)+1} `{k}` ({len(cntr)} distinct values)\n\n")
            f.write(f"- Distinct values: {len(cntr)}\n")
            f.write(f"- Case variants count: {len(variants)}\n")
            if variants:
                f.write(f"  - Examples: {list(variants.items())[:5]}\n")
            f.write(f"- Leading/trailing whitespace count: {len(ws)}\n")
            if ws:
                f.write(f"  - Values with whitespace: {list(ws)[:5]}\n")
            f.write("\nTop 15 values:\n\n")
            f.write("| Value | Count | Percentage |\n")
            f.write("| --- | ---: | ---: |\n")
            for val, cnt in cntr.most_common(15):
                f.write(f"| `{val}` | {cnt:,} | {(cnt/n_products)*100:.2f}% |\n")
            f.write("\n")

        # 3. Name Quirks and Vocabulary
        f.write("## 3. Product Name Quirks and Vocabulary\n\n")
        f.write(f"- Distinct Product Names: **{len(name_counter):,}** (average {(n_products/len(name_counter)):.2f} products per name)\n")
        f.write(f"- Length (chars): min={name_lengths[0]}, p25={percentile(name_lengths, 0.25):.0f}, median={percentile(name_lengths, 0.5):.0f}, p75={percentile(name_lengths, 0.75):.0f}, p95={percentile(name_lengths, 0.95):.0f}, max={name_lengths[-1]}\n")
        f.write(f"- Capitalization: Title/Standard={n_products - all_caps_names - lower_case_names:,}, ALL CAPS={all_caps_names:,}, all lower={lower_case_names:,}\n")
        f.write(f"- Non-ASCII characters: {dict(non_ascii_names)}\n")
        f.write(f"- Frequent punctuation marks: {dict(punct_names.most_common(10))}\n")
        f.write(f"- Pack patterns: {dict(digit_pattern_names.most_common(10))}\n\n")

        f.write("### Top 200 Name Tokens\n\n")
        f.write("| Rank | Token | Count | Rank | Token | Count | Rank | Token | Count | Rank | Token | Count |\n")
        f.write("| ---: | --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | --- | ---: |\n")
        top200 = name_tokens.most_common(200)
        for i in range(0, min(200, len(top200)), 4):
            row = []
            for j in range(4):
                if i + j < len(top200):
                    tok, cnt = top200[i + j]
                    row.extend([str(i + j + 1), f"`{tok}`", f"{cnt:,}"])
                else:
                    row.extend(["", "", ""])
            f.write("| " + " | ".join(row) + " |\n")
        f.write("\n")

        f.write("### Frequent Short Tokens (Abbreviation Candidates)\n\n")
        f.write("| Token | Count | Likely Meaning in Fashion |\n")
        f.write("| --- | ---: | --- |\n")
        for tok, cnt in abbr_candidates.most_common(30):
            f.write(f"| `{tok}` | {cnt:,} | Pending confirmation |\n")
        f.write("\n")

        # 4. Description Quirks and Attributes
        f.write("## 4. Description Quirks and Extracted Attributes\n\n")
        f.write(f"- Descriptions Present: **{len(desc_lengths):,}** ({(len(desc_lengths)/n_products)*100:.2f}%)\n")
        if desc_lengths:
            f.write(f"- Length (chars): min={desc_lengths[0]}, p25={percentile(desc_lengths, 0.25):.0f}, median={percentile(desc_lengths, 0.5):.0f}, p75={percentile(desc_lengths, 0.75):.0f}, p95={percentile(desc_lengths, 0.95):.0f}, max={desc_lengths[-1]}\n\n")

        f.write("### Top Repeated Description Boilerplate / Openings\n\n")
        for phrase, cnt in desc_phrases.most_common(10):
            f.write(f"- `{phrase}` ({cnt:,} occurrences)\n")
        f.write("\n")

        f.write("### Extracted Attribute Mentions (Name vs Description)\n\n")
        f.write("| Attribute Category | Keyword | In Name | In Description |\n")
        f.write("| --- | --- | ---: | ---: |\n")
        for group, kws in [
            ("Material", material_keywords),
            ("Fit", fit_keywords),
            ("Neckline", neck_keywords),
            ("Sleeve", sleeve_keywords),
            ("Length", length_keywords),
            ("Closure", closure_keywords),
            ("Occasion/Style", occasion_keywords)
        ]:
            for kw in kws:
                nm = attr_name_mentions.get(kw, 0)
                dm = attr_desc_mentions.get(kw, 0)
                if nm > 0 or dm > 0:
                    f.write(f"| {group} | `{kw}` | {nm:,} | {dm:,} |\n")
        f.write("\n")

        # 5. Price and Rating Distributions
        f.write("## 5. Price, Rating, and Review Distributions\n\n")
        f.write(f"- Overall Price (INR): min={prices[0]}, p10={percentile(prices, 0.1):.0f}, p25={percentile(prices, 0.25):.0f}, median={percentile(prices, 0.5):.0f}, p75={percentile(prices, 0.75):.0f}, p90={percentile(prices, 0.9):.0f}, p99={percentile(prices, 0.99):.0f}, max={prices[-1]}\n")
        f.write(f"- Rated Products: **{len(ratings):,}** ({(len(ratings)/n_products)*100:.2f}%)\n")
        f.write(f"- Unrated (Null average): **{n_products - len(ratings):,}** ({((n_products - len(ratings))/n_products)*100:.2f}%)\n")
        if ratings:
            f.write(f"- Ratings (when present): min={ratings[0]:.2f}, median={percentile(ratings, 0.5):.2f}, mean={statistics.mean(ratings):.2f}, max={ratings[-1]:.2f}\n")
        f.write(f"- Review counts: min={review_counts[0]}, median={percentile(review_counts, 0.5):.0f}, p90={percentile(review_counts, 0.9):.0f}, max={review_counts[-1]}\n\n")

        f.write("### Price Percentiles for Top 10 Product Types\n\n")
        f.write("| Product Type | Count | Min | Median | P75 | Max |\n")
        f.write("| --- | ---: | ---: | ---: | ---: | ---: |\n")
        for ptype, _ in cat_counts["product_type"].most_common(10):
            pt_prices = sorted(price_by_type[ptype])
            if pt_prices:
                f.write(f"| `{ptype}` | {len(pt_prices):,} | {pt_prices[0]:.0f} | {percentile(pt_prices, 0.5):.0f} | {percentile(pt_prices, 0.75):.0f} | {pt_prices[-1]:.0f} |\n")
        f.write("\n")

        # 6. Duplicates and Variants
        f.write("## 6. Duplicate Names and Product Variants\n\n")
        f.write("Top 10 Most Frequent Product Names (Color/Style Variants):\n\n")
        f.write("| Product Name | Number of Products (Variants) |\n")
        f.write("| --- | ---: |\n")
        for nm, cnt in name_counter.most_common(10):
            f.write(f"| `{nm}` | {cnt:,} |\n")
        f.write("\n")

        # 7. Category Overlaps and Ambiguities
        f.write("## 7. Product Type Cross-Category Overlaps and Ambiguities\n\n")
        f.write("Product types that appear under multiple categories:\n\n")
        multi_cat_types = {pt: cats for pt, cats in type_category_map.items() if len(cats) > 1}
        f.write(f"- Total product types with multiple categories: **{len(multi_cat_types)}**\n\n")
        f.write("| Product Type | Associated Categories |\n")
        f.write("| --- | --- |\n")
        for pt, cats in sorted(multi_cat_types.items(), key=lambda x: cat_counts["product_type"][x[0]], reverse=True)[:20]:
            f.write(f"| `{pt}` | {', '.join(sorted(cats))} |\n")
        f.write("\n")

    print(f"Profile written to {OUTPUT_MD}")

    # Also dump raw profile stats to json for downstream scripts
    raw_stats = {
        "n_products": n_products,
        "null_counts": dict(null_counts),
        "cat_counts": {k: dict(v) for k, v in cat_counts.items()},
        "name_tokens_top500": name_tokens.most_common(500),
        "multi_cat_types": {k: list(v) for k, v in multi_cat_types.items()},
        "price_stats": {
            "overall": {
                "min": prices[0], "p10": percentile(prices, 0.1), "p25": percentile(prices, 0.25),
                "median": percentile(prices, 0.5), "p75": percentile(prices, 0.75),
                "p90": percentile(prices, 0.9), "p99": percentile(prices, 0.99), "max": prices[-1]
            }
        }
    }
    with open(DERIVED_DIR / "raw_profile.json", "w", encoding="utf-8") as f:
        json.dump(raw_stats, f, indent=2)
    print("Profile data dumped to data_derived/raw_profile.json")


if __name__ == "__main__":
    profile()
