"""Literal attribute mining from product name and description."""
import re
from seo.normalize import normalize_text

MATERIALS = [
    "cotton", "polyester", "elastane", "viscose", "linen", "wool", "silk",
    "denim", "leather", "nylon", "fleece", "jersey", "chiffon", "satin",
    "velvet", "twill", "modal", "cashmere", "acrylic", "canvas", "suede",
    "flannel", "poplin", "jacquard", "lace", "mesh", "knit", "ribbed"
]

FITS = [
    "regular fit", "slim fit", "skinny fit", "relaxed fit", "loose fit",
    "oversized", "tight fit", "wide leg", "straight leg", "tapered",
    "flared", "bootcut", "boyfriend", "mom fit", "tailored"
]

NECKLINES = [
    "round neck", "v-neck", "crew neck", "boat neck", "halterneck",
    "turtleneck", "high neck", "hooded", "polo collar", "collared",
    "sweetheart neckline", "square neckline", "off-the-shoulder", "mandarin collar"
]

SLEEVES = [
    "sleeveless", "short sleeve", "long sleeve", "3/4 sleeve", "cap sleeve",
    "drop shoulder", "puff sleeve", "raglan sleeve", "flutter sleeve"
]

LENGTHS = [
    "mini", "midi", "maxi", "cropped", "ankle length", "knee length",
    "calf length", "full length", "short", "long"
]

CLOSURES = [
    "button", "zip", "zipper", "elasticated", "drawstring", "tie belt",
    "press stud", "hook-and-eye", "snap", "pull-on", "concealed zip"
]

OCCASIONS = [
    "casual", "party", "wedding", "office", "formal", "work", "summer",
    "winter", "beach", "gym", "workout", "sport", "running", "yoga",
    "sleepwear", "lounge", "loungewear", "festive", "holiday", "outdoor"
]

ALL_ATTRIBUTES = {
    "material": MATERIALS,
    "fit": FITS,
    "neckline": NECKLINES,
    "sleeve": SLEEVES,
    "length": LENGTHS,
    "closure": CLOSURES,
    "occasion": OCCASIONS
}


def mine_attributes(name: str, description: str) -> dict:
    """Mine literal attribute mentions tagged by source (name vs description)."""
    norm_name = normalize_text(name or "")
    norm_desc = normalize_text(description or "")

    mined_name = {}
    mined_desc = {}

    for cat, terms in ALL_ATTRIBUTES.items():
        found_name = []
        found_desc = []
        for term in terms:
            # Word boundary check for literal presence
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, norm_name):
                found_name.append(term)
            if re.search(pattern, norm_desc):
                found_desc.append(term)
        if found_name:
            mined_name[cat] = found_name
        if found_desc:
            mined_desc[cat] = found_desc

    return {
        "name_attrs": mined_name,
        "desc_attrs": mined_desc
    }
