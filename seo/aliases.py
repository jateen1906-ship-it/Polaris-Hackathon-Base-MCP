"""Alias, synonym, and abbreviation tables mapping to exact catalog values."""
import json
from pathlib import Path

# Evidence counts from catalog profiling (see docs/data_profile.md):
# tee: 4,539
# trs: 1,428
# jkt: 532
# blz: 239
# pj: 1,107
# hw: 1,473
# ls: 2,336
# ss: 1,638
ABBREVIATION_EVIDENCE = {
    "tee": {"target": "T-shirt", "evidence_count": 4539},
    "trs": {"target": "Trousers", "evidence_count": 1428},
    "jkt": {"target": "Jacket", "evidence_count": 532},
    "blz": {"target": "Blazer", "evidence_count": 239},
    "pj": {"target": "Pyjama set", "evidence_count": 1107},
    "sw": {"target": "Sweater", "evidence_count": 226},
}

# Synonyms and colloquial terms mapping to catalog values
# Every target value MUST exist in the catalog dataset.
PRODUCT_TYPE_ALIASES = {
    # T-shirts / Tops
    "top": "Top",
    "tops": "Top",
    "tee": "T-shirt",
    "tees": "T-shirt",
    "tshirt": "T-shirt",
    "t shirt": "T-shirt",
    "t-shirts": "T-shirt",
    "tee shirt": "T-shirt",
    "tank": "Vest top",
    "tanktop": "Vest top",
    "tank top": "Vest top",
    "singlet": "Vest top",
    "sleeveless top": "Vest top",
    "camisole": "Vest top",
    "cami": "Vest top",
    "crop top": "Top",
    "jumper": "Sweater",
    "jumpers": "Sweater",
    "pullover": "Sweater",
    "knit sweater": "Sweater",
    "knitwear": "Sweater",
    "polo": "Polo shirt",
    "polos": "Polo shirt",

    # Bottoms
    "pants": "Trousers",
    "pant": "Trousers",
    "trousers": "Trousers",
    "trouser": "Trousers",
    "slacks": "Trousers",
    "chinos": "Trousers",
    "chino": "Trousers",
    "jeans": "Trousers",
    "jean": "Trousers",
    "denims": "Trousers",
    "denim pants": "Trousers",
    "joggers": "Trousers",
    "jogger": "Trousers",
    "sweatpants": "Trousers",
    "track pants": "Trousers",
    "cargos": "Trousers",
    "cargo pants": "Trousers",
    "tights": "Leggings/Tights",
    "leggings": "Leggings/Tights",
    "legging": "Leggings/Tights",
    "short": "Shorts",
    "bermudas": "Shorts",
    "mini skirt": "Skirt",
    "maxi skirt": "Skirt",

    # Dresses
    "dresses": "Dress",
    "frock": "Dress",
    "frocks": "Dress",
    "gown": "Dress",
    "gowns": "Dress",
    "maxi dress": "Dress",
    "mini dress": "Dress",
    "midi dress": "Dress",
    "jumpsuit": "Jumpsuit/Playsuit",
    "playsuit": "Jumpsuit/Playsuit",
    "romper": "Jumpsuit/Playsuit",
    "dungaree": "Dungarees",
    "overalls": "Dungarees",

    # Outerwear
    "jackets": "Jacket",
    "jkt": "Jacket",
    "blazer": "Blazer",
    "blz": "Blazer",
    "blazers": "Blazer",
    "suit jacket": "Blazer",
    "coats": "Coat",
    "overcoat": "Coat",
    "parka": "Coat",
    "windbreaker": "Jacket",
    "bomber": "Jacket",
    "bomber jacket": "Jacket",
    "denim jacket": "Jacket",
    "leather jacket": "Jacket",
    "gilet": "Outdoor Waistcoat",
    "waistcoat": "Tailored Waistcoat",

    # Footwear
    "shoes": "Sneakers",
    "shoe": "Sneakers",
    "trainers": "Sneakers",
    "trainer": "Sneakers",
    "sneakers": "Sneakers",
    "sneaker": "Sneakers",
    "kicks": "Sneakers",
    "running shoes": "Sneakers",
    "boots": "Boots",
    "boot": "Boots",
    "ankle boots": "Boots",
    "sandals": "Sandals",
    "sandal": "Sandals",
    "flip flops": "Flip flop",
    "flip-flops": "Flip flop",
    "thongs": "Flip flop",
    "slippers": "Slippers",
    "slipper": "Slippers",
    "loafers": "Flat shoe",
    "loafer": "Flat shoe",
    "heels": "Heels",
    "heel": "Heels",
    "high heels": "Heels",
    "stiletto": "Heels",
    "pumps": "Pumps",
    "pump": "Pumps",
    "moccasins": "Moccasins",
    "moccasin": "Moccasins",
    "pre-walkers": "Pre-walkers",
    "pre-walker": "Pre-walkers",
    "pre walkers": "Pre-walkers",
    "pre walker": "Pre-walkers",
    "flats": "Flat shoe",
    "ballerina": "Ballerinas",

    # Bags
    "bag": "Bag",
    "bags": "Bag",
    "handbag": "Bag",
    "handbags": "Bag",
    "purse": "Bag",
    "purses": "Bag",
    "tote": "Tote bag",
    "backpacks": "Backpack",
    "rucksack": "Backpack",
    "clutch": "Bag",
    "crossbody": "Cross-body bag",
    "cross body": "Cross-body bag",
    "shoulder bag": "Shoulder bag",
    "gym bag": "Weekend/Gym bag",
    "duffle": "Weekend/Gym bag",

    # Accessories
    "belt": "Belt",
    "belts": "Belt",
    "scarf": "Scarf",
    "scarves": "Scarf",
    "muffler": "Scarf",
    "hat": "Hat/beanie",
    "hats": "Hat/beanie",
    "cap": "Cap",
    "caps": "Cap",
    "beanie": "Beanie",
    "beanies": "Beanie",
    "sunglasses": "Sunglasses",
    "sunnies": "Sunglasses",
    "shades": "Sunglasses",
    "shades sunglasses": "Sunglasses",
    "shades eyewear": "Sunglasses",
    "eyeglasses": "Eyeglasses",
    "eyeglass": "Eyeglasses",
    "glasses": "Eyeglasses",
    "gloves": "Gloves",
    "glove": "Gloves",
    "mittens": "Gloves",
    "chem cosmetics": "Chem. cosmetics",
    "chem. cosmetics": "Chem. cosmetics",
    "cosmetics": "Chem. cosmetics",
    "cosmetic": "Chem. cosmetics",
    "socks": "Socks",
    "sock": "Socks",

    # Jewellery
    "earrings": "Earrings",
    "earring": "Earrings",
    "necklace": "Necklace",
    "necklaces": "Necklace",
    "chain": "Necklace",
    "pendant": "Necklace",
    "ring": "Ring",
    "rings": "Ring",
    "bracelet": "Bracelet",
    "bracelets": "Bracelet",
    "bangle": "Bracelet",

    # Underwear & Nightwear
    "bra": "Bra",
    "bras": "Bra",
    "undies": "Underwear bottom",
    "briefs": "Underwear bottom",
    "panties": "Underwear bottom",
    "boxers": "Underwear bottom",
    "underwear": "Underwear bottom",
    "pyjamas": "Pyjama set",
    "pajamas": "Pyjama set",
    "pj": "Pyjama set",
    "pjs": "Pyjama set",
    "sleepwear": "Pyjama set",
    "nightdress": "Night gown",
    "nightie": "Night gown",
    "nightgown": "Night gown",
    "dressing gown": "Robe",
    "bathrobe": "Robe",

    # Swimwear
    "swimsuit": "Swimsuit",
    "swimming costume": "Swimsuit",
    "bathers": "Swimsuit",
    "bikini": "Bikini top",
    "swimwear": "Swimsuit",
    "trunks": "Swimwear bottom"
}

CATEGORY_ALIASES = {
    "top": "Garment Upper body",
    "tops": "Garment Upper body",
    "upper": "Garment Upper body",
    "upper body": "Garment Upper body",
    "bottom": "Garment Lower body",
    "bottoms": "Garment Lower body",
    "lower": "Garment Lower body",
    "lower body": "Garment Lower body",
    "full body": "Garment Full body",
    "dress": "Garment Full body",
    "dresses": "Garment Full body",
    "footwear": "Shoes",
    "shoes": "Shoes",
    "bag": "Bags",
    "bags": "Bags",
    "accessory": "Accessories",
    "accessories": "Accessories",
    "swim": "Swimwear",
    "swimwear": "Swimwear",
    "night": "Nightwear",
    "nightwear": "Nightwear",
    "sleepwear": "Nightwear",
    "undies": "Underwear",
    "underwear": "Underwear",
    "socks": "Socks & Tights",
    "tights": "Socks & Tights",
    "makeup": "Cosmetic",
    "cosmetics": "Cosmetic"
}

AUDIENCE_ALIASES = {
    # Women
    "women": "Ladieswear",
    "woman": "Ladieswear",
    "womens": "Ladieswear",
    "womenswear": "Ladieswear",
    "female": "Ladieswear",
    "ladies": "Ladieswear",
    "ladieswear": "Ladieswear",
    "lady": "Ladieswear",

    # Men
    "men": "Menswear",
    "man": "Menswear",
    "mens": "Menswear",
    "menswear": "Menswear",
    "male": "Menswear",
    "gents": "Menswear",
    "gent": "Menswear",
    "gentlemen": "Menswear",

    # Kids
    "kids": "Children Sizes 92-140",
    "kid": "Children Sizes 92-140",
    "children": "Children Sizes 92-140",
    "child": "Children Sizes 92-140",
    "boys": "Children Sizes 92-140",
    "boy": "Children Sizes 92-140",
    "girls": "Children Sizes 92-140",
    "girl": "Children Sizes 92-140",
    "teen": "Children Sizes 134-170",
    "teens": "Children Sizes 134-170",

    # Baby
    "baby": "Baby Sizes 50-98",
    "babies": "Baby Sizes 50-98",
    "infant": "Baby Sizes 50-98",
    "toddler": "Baby Sizes 50-98",
    "newborn": "Baby Sizes 50-98",

    # Sport
    "sport": "Sport",
    "sports": "Sport",
    "sportswear": "Sport",
    "activewear": "Sport",
    "athletic": "Sport",
    "gym": "Sport",
    "fitness": "Sport"
}

COLOR_ALIASES = {
    # Dark Blue / Navy
    "navy": "Dark Blue",
    "navy blue": "Dark Blue",
    "midnight blue": "Dark Blue",
    "indigo": "Dark Blue",

    # Light Blue / Sky
    "sky blue": "Light Blue",
    "baby blue": "Light Blue",
    "ice blue": "Light Blue",

    # Dark Red / Maroon / Burgundy
    "maroon": "Dark Red",
    "burgundy": "Dark Red",
    "wine": "Dark Red",
    "crimson": "Dark Red",
    "ruby": "Dark Red",

    # Green variants
    "olive": "Greenish Khaki",
    "khaki": "Greenish Khaki",
    "army green": "Greenish Khaki",
    "forest green": "Dark Green",
    "mint": "Light Green",
    "sage": "Light Green",
    "emerald": "Dark Green",

    # Grey variants
    "charcoal": "Dark Grey",
    "slate": "Dark Grey",
    "anthracite": "Dark Grey",
    "silver": "Silver",

    # Beige / Off White / Tan / Cream
    "cream": "Off White",
    "ivory": "Off White",
    "ecru": "Off White",
    "tan": "Beige",
    "nude": "Light Beige",
    "camel": "Beige",
    "sand": "Beige",
    "taupe": "Greyish Beige",

    # Pink variants
    "rose": "Light Pink",
    "blush": "Light Pink",
    "dusty pink": "Light Pink",
    "fuchsia": "Dark Pink",
    "magenta": "Dark Pink",
    "hot pink": "Dark Pink",

    # Purple variants
    "violet": "Purple",
    "lavender": "Light Purple",
    "lilac": "Light Purple",
    "plum": "Dark Purple",

    # Brown / Rust
    "brown": "Yellowish Brown",
    "rust": "Dark Orange",
    "copper": "Bronze/Copper",
    "gold": "Gold",

    # Base Colors mapping directly
    "black": "Black",
    "white": "White",
    "blue": "Blue",
    "red": "Red",
    "green": "Green",
    "grey": "Grey",
    "gray": "Grey",
    "yellow": "Yellow",
    "orange": "Orange",
    "pink": "Pink",
    "purple": "Purple",
    "turquoise": "Turquoise",
    "beige": "Beige"
}

PATTERN_ALIASES = {
    "plain": "Solid",
    "solid": "Solid",
    "basic": "Solid",
    "stripes": "Stripe",
    "striped": "Stripe",
    "pinstripe": "Stripe",
    "checks": "Check",
    "checked": "Check",
    "plaid": "Check",
    "tartan": "Check",
    "gingham": "Check",
    "houndstooth": "Check",
    "dots": "Dot",
    "polka dot": "Dot",
    "polka dots": "Dot",
    "spotted": "Dot",
    "floral": "All over pattern",
    "flowers": "All over pattern",
    "flower print": "All over pattern",
    "printed": "All over pattern",
    "print": "All over pattern",
    "patterned": "All over pattern",
    "animal print": "All over pattern",
    "leopard": "All over pattern",
    "zebra": "All over pattern",
    "heather": "Melange",
    "mottled": "Melange",
    "sparkly": "Glittering/Metallic",
    "glitter": "Glittering/Metallic",
    "shimmer": "Glittering/Metallic",
    "sequins": "Sequin",
    "denim": "Denim"
}


def validate_all_aliases(valid_values: dict[str, set[str]]):
    """Ensure every single alias targets a value that really exists in the catalog."""
    tables = [
        ("product_type", PRODUCT_TYPE_ALIASES),
        ("category", CATEGORY_ALIASES),
        ("audience", AUDIENCE_ALIASES),
        ("color", COLOR_ALIASES),
        ("pattern", PATTERN_ALIASES)
    ]
    for field_name, alias_dict in tables:
        known = valid_values[field_name]
        for src, target in alias_dict.items():
            assert target in known, f"Integrity error: alias '{src}' -> '{target}' for field '{field_name}' does not exist in catalog!"
    print("All alias targets verified against catalog values.")


def save_aliases(output_path: Path):
    data = {
        "abbreviations": ABBREVIATION_EVIDENCE,
        "product_type": PRODUCT_TYPE_ALIASES,
        "category": CATEGORY_ALIASES,
        "audience": AUDIENCE_ALIASES,
        "color": COLOR_ALIASES,
        "pattern": PATTERN_ALIASES
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
