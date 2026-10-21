"""Color taxonomy, color families, and hard matching logic."""
import json
from pathlib import Path

# Mapping of all 50 catalog colors to canonical base color families
COLOR_TO_BASE = {
    "Black": "black",
    "White": "white",
    "Off White": "white",
    "Blue": "blue",
    "Dark Blue": "blue",
    "Light Blue": "blue",
    "Other Blue": "blue",
    "Red": "red",
    "Dark Red": "red",
    "Light Red": "red",
    "Other Red": "red",
    "Green": "green",
    "Dark Green": "green",
    "Light Green": "green",
    "Greenish Khaki": "green",
    "Other Green": "green",
    "Grey": "grey",
    "Dark Grey": "grey",
    "Light Grey": "grey",
    "Greyish Beige": "grey",
    "Beige": "beige",
    "Dark Beige": "beige",
    "Light Beige": "beige",
    "Pink": "pink",
    "Dark Pink": "pink",
    "Light Pink": "pink",
    "Other Pink": "pink",
    "Yellow": "yellow",
    "Dark Yellow": "yellow",
    "Light Yellow": "yellow",
    "Other Yellow": "yellow",
    "Orange": "orange",
    "Dark Orange": "orange",
    "Light Orange": "orange",
    "Other Orange": "orange",
    "Yellowish Brown": "brown",
    "Purple": "purple",
    "Dark Purple": "purple",
    "Light Purple": "purple",
    "Other Purple": "purple",
    "Turquoise": "turquoise",
    "Dark Turquoise": "turquoise",
    "Light Turquoise": "turquoise",
    "Other Turquoise": "turquoise",
    "Gold": "metallic",
    "Silver": "metallic",
    "Bronze/Copper": "metallic",
    "Transparent": "other",
    "Other": "other",
    "Unknown": "other"
}

# Group catalog colors by base color family
BASE_TO_COLORS = {}
for c, base in COLOR_TO_BASE.items():
    BASE_TO_COLORS.setdefault(base, set()).add(c)


def get_base_color(color_name: str) -> str:
    """Return the base color family for a catalog color."""
    return COLOR_TO_BASE.get(color_name, "other")


def get_colors_in_family(base_color: str) -> set[str]:
    """Return all catalog colors belonging to this base color family."""
    return BASE_TO_COLORS.get(base_color.lower(), set())


def color_matches(product_color: str, query_color: str, strict_base: bool = True) -> bool:
    """Check if product color matches query color.
    If query is 'black', only 'Black' matches (hard constraint).
    If query is 'white', 'White' or 'Off White' can match.
    If query is 'navy', 'Dark Blue' matches.
    """
    prod_c = product_color.strip().casefold()
    q_c = query_color.strip().casefold()

    if prod_c == q_c:
        return True

    # Exact base color logic
    if q_c == "black":
        return prod_c == "black"

    prod_base = COLOR_TO_BASE.get(product_color, "other")
    if strict_base:
        return prod_base == q_c

    return False
