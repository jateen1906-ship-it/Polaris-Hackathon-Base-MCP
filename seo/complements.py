"""Complement graph derived from taxonomy and type families."""
import json
from pathlib import Path
from seo.taxonomy import PRODUCT_TYPE_TO_FAMILIES

# Complementary type family associations
# Substitutes within the same type family are strictly prohibited.
FAMILY_COMPLEMENTS = {
    "dresses": ["bags", "footwear", "jewellery", "outerwear"],
    "tops": ["bottoms", "footwear", "outerwear", "accessories"],
    "bottoms": ["tops", "footwear", "outerwear", "accessories"],
    "outerwear": ["accessories", "footwear", "bags"],
    "footwear": ["accessories", "bags"],
    "swimwear": ["accessories", "footwear", "bags"],
    "nightwear": ["footwear"],
    "activewear": ["footwear", "bags", "accessories"]
}

# Preferred accessory/complement product types per primary family
FAMILY_PREFERRED_TYPES = {
    "dresses": ["Bag", "Tote bag", "Shoulder bag", "Cross-body bag", "Heels", "Heeled sandals", "Ballerinas", "Sandals", "Earrings", "Necklace", "Bracelet", "Blazer", "Jacket"],
    "tops": ["Trousers", "Shorts", "Skirt", "Sneakers", "Boots", "Jacket", "Coat", "Belt"],
    "bottoms": ["T-shirt", "Top", "Shirt", "Blouse", "Sweater", "Sneakers", "Boots", "Sandals", "Belt", "Jacket"],
    "outerwear": ["Scarf", "Beanie", "Hat/beanie", "Gloves", "Boots", "Bag", "Cross-body bag"],
    "footwear": ["Socks", "Bag", "Backpack", "Belt"],
    "swimwear": ["Sunglasses", "Flip flop", "Sandals", "Tote bag", "Straw hat", "Sarong"],
    "nightwear": ["Slippers", "Robe"],
    "activewear": ["Sneakers", "Weekend/Gym bag", "Cap", "Waterbottle"]
}


def get_complementary_families(primary_family: str) -> list[str]:
    """Return complementary families for a primary family. Never returns the primary family itself."""
    return FAMILY_COMPLEMENTS.get(primary_family, ["accessories", "bags", "footwear"])


def get_complementary_product_types(primary_product_type: str) -> list[str]:
    """Return valid complementary product types for a primary product type."""
    families = PRODUCT_TYPE_TO_FAMILIES.get(primary_product_type, [])
    complements = []
    for fam in families:
        types = FAMILY_PREFERRED_TYPES.get(fam, [])
        for t in types:
            if t not in complements and t != primary_product_type:
                # Ensure it's not a substitute (doesn't share the same family)
                target_fams = set(PRODUCT_TYPE_TO_FAMILIES.get(t, []))
                if fam not in target_fams:
                    complements.append(t)
    return complements


def build_complement_graph() -> dict:
    """Build complete complement graph for all catalog product types."""
    graph = {}
    for ptype in PRODUCT_TYPE_TO_FAMILIES:
        comp_types = get_complementary_product_types(ptype)
        if comp_types:
            graph[ptype] = comp_types
    return {
        "family_complements": FAMILY_COMPLEMENTS,
        "type_complements": graph
    }


def save_complements(output_path: Path):
    graph = build_complement_graph()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
