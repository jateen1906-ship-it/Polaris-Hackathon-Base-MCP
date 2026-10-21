"""Canonical taxonomy and type families mapping for catalog products."""
import json
from pathlib import Path

# Mapping of all 131 catalog product_types to one or more primary type families
PRODUCT_TYPE_TO_FAMILIES = {
    # Tops
    "T-shirt": ["tops"],
    "Top": ["tops"],
    "Blouse": ["tops"],
    "Shirt": ["tops"],
    "Vest top": ["tops"],
    "Sweater": ["tops"],
    "Cardigan": ["tops", "outerwear"],
    "Hoodie": ["tops", "outerwear"],
    "Polo shirt": ["tops"],
    "Bodysuit": ["tops", "underwear"],
    "Tailored Waistcoat": ["tops", "outerwear"],
    "Outdoor Waistcoat": ["tops", "outerwear"],
    "Kids Underwear top": ["tops", "underwear"],

    # Bottoms
    "Trousers": ["bottoms"],
    "Shorts": ["bottoms"],
    "Skirt": ["bottoms"],
    "Leggings/Tights": ["bottoms", "socks_tights"],
    "Dungarees": ["bottoms", "dresses"],
    "Outdoor trousers": ["bottoms"],
    "Long John": ["bottoms", "underwear"],

    # Dresses and Full-body
    "Dress": ["dresses"],
    "Jumpsuit/Playsuit": ["dresses"],
    "Costumes": ["dresses"],
    "Outdoor overall": ["dresses", "outerwear"],
    "Garment Set": ["dresses", "tops", "bottoms"],

    # Outerwear
    "Jacket": ["outerwear"],
    "Coat": ["outerwear"],
    "Blazer": ["outerwear"],

    # Footwear
    "Boots": ["footwear"],
    "Sneakers": ["footwear"],
    "Sandals": ["footwear"],
    "Ballerinas": ["footwear"],
    "Heels": ["footwear"],
    "Slippers": ["footwear"],
    "Flip flop": ["footwear"],
    "Pumps": ["footwear"],
    "Flat shoe": ["footwear"],
    "Flat shoes": ["footwear"],
    "Heeled sandals": ["footwear"],
    "Moccasins": ["footwear"],
    "Bootie": ["footwear"],
    "Pre-walkers": ["footwear"],
    "Other shoe": ["footwear"],
    "Wedge": ["footwear"],

    # Bags
    "Bag": ["bags"],
    "Backpack": ["bags"],
    "Tote bag": ["bags"],
    "Shoulder bag": ["bags"],
    "Cross-body bag": ["bags"],
    "Bumbag": ["bags"],
    "Weekend/Gym bag": ["bags"],
    "Wallet": ["bags", "accessories"],
    "Washing bag": ["bags"],

    # Jewellery
    "Earring": ["jewellery"],
    "Earrings": ["jewellery"],
    "Necklace": ["jewellery"],
    "Bracelet": ["jewellery"],
    "Ring": ["jewellery"],

    # Accessories
    "Belt": ["accessories"],
    "Scarf": ["accessories"],
    "Cap": ["accessories"],
    "Beanie": ["accessories"],
    "Hat/beanie": ["accessories"],
    "Hat/brim": ["accessories"],
    "Bucket hat": ["accessories"],
    "Straw hat": ["accessories"],
    "Felt hat": ["accessories"],
    "Cap/peaked": ["accessories"],
    "Sunglasses": ["accessories"],
    "Eyeglasses": ["accessories"],
    "Gloves": ["accessories"],
    "Tie": ["accessories"],
    "Braces": ["accessories"],
    "Hair clip": ["accessories"],
    "Hair ties": ["accessories"],
    "Hair string": ["accessories"],
    "Hair/alice band": ["accessories"],
    "Hairband": ["accessories"],
    "Headband": ["accessories"],
    "Alice band": ["accessories"],
    "Watch": ["accessories"],
    "Umbrella": ["accessories"],
    "Accessories set": ["accessories"],
    "Keychain": ["accessories"],
    "Mobile case": ["accessories"],
    "Wireless earphone case": ["accessories"],
    "Other accessories": ["accessories"],
    "Leg warmers": ["accessories", "socks_tights"],

    # Underwear
    "Bra": ["underwear"],
    "Underwear bottom": ["underwear"],
    "Underwear body": ["underwear"],
    "Underwear corset": ["underwear"],
    "Underwear set": ["underwear"],
    "Underwear Tights": ["underwear", "socks_tights"],
    "Bra extender": ["underwear"],
    "Nipple covers": ["underwear"],
    "Underdress": ["underwear"],

    # Nightwear
    "Pyjama set": ["nightwear"],
    "Pyjama bottom": ["nightwear"],
    "Pyjama jumpsuit/playsuit": ["nightwear"],
    "Night gown": ["nightwear"],
    "Robe": ["nightwear"],
    "Sleep Bag": ["nightwear"],
    "Sleeping sack": ["nightwear"],

    # Swimwear
    "Swimsuit": ["swimwear"],
    "Bikini top": ["swimwear"],
    "Swimwear bottom": ["swimwear"],
    "Swimwear set": ["swimwear"],
    "Swimwear top": ["swimwear"],
    "Sarong": ["swimwear", "accessories"],

    # Socks
    "Socks": ["socks_tights"],

    # Lifestyle, Pets, Cosmetics, Items
    "Dog Wear": ["lifestyle_home_pet"],
    "Dog wear": ["lifestyle_home_pet"],
    "Blanket": ["lifestyle_home_pet"],
    "Cushion": ["lifestyle_home_pet"],
    "Towel": ["lifestyle_home_pet"],
    "Waterbottle": ["lifestyle_home_pet"],
    "Soft Toys": ["lifestyle_home_pet"],
    "Toy": ["lifestyle_home_pet"],
    "Giftbox": ["lifestyle_home_pet"],
    "Marker pen": ["lifestyle_home_pet"],
    "Sewing kit": ["lifestyle_home_pet"],
    "Stain remover spray": ["lifestyle_home_pet"],
    "Side table": ["lifestyle_home_pet"],
    "Wood balls": ["lifestyle_home_pet"],
    "Zipper head": ["lifestyle_home_pet"],
    "Baby Bib": ["lifestyle_home_pet", "accessories"],
    "Chem. cosmetics": ["lifestyle_home_pet"],
    "Fine cosmetics": ["lifestyle_home_pet"],
    "Clothing mist": ["lifestyle_home_pet"],
    "Unknown": ["lifestyle_home_pet"]
}


def build_taxonomy_tree(products: list[dict]) -> dict:
    """Build a canonical hierarchy tree: section -> audience -> category -> product_type."""
    tree = {}
    for p in products:
        sec = p.get("section") or "Unknown"
        aud = p.get("audience") or "Unknown"
        cat = p.get("category") or "Unknown"
        ptype = p.get("product_type") or "Unknown"

        if sec not in tree:
            tree[sec] = {}
        if aud not in tree[sec]:
            tree[sec][aud] = {}
        if cat not in tree[sec][aud]:
            tree[sec][aud][cat] = set()
        tree[sec][aud][cat].add(ptype)

    # Convert sets to sorted lists for JSON serialization
    serialized_tree = {}
    for s_k, s_v in tree.items():
        serialized_tree[s_k] = {}
        for a_k, a_v in s_v.items():
            serialized_tree[s_k][a_k] = {}
            for c_k, c_v in a_v.items():
                serialized_tree[s_k][a_k][c_k] = sorted(list(c_v))

    return {
        "tree": serialized_tree,
        "type_to_families": PRODUCT_TYPE_TO_FAMILIES
    }


def save_taxonomy(output_path: Path, taxonomy_data: dict):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(taxonomy_data, f, indent=2)
