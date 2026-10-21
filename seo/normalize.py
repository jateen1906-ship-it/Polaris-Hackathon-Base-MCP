"""Text normalization, tokenization, stemming, and price/budget extraction."""
import re
import unicodedata
from functools import lru_cache

# Words where naive suffix stripping hurts fashion semantics
STEM_EXCEPTIONS = {
    "jeans", "glasses", "sunglasses", "eyeglasses", "boxers", "tights", "leggings",
    "pyjamas", "slacks", "shorts", "pants", "underpants", "trunks",
    "dungarees", "braces", "clothes", "basics", "dress", "dresses",
    "canvas", "series", "species", "chinos", "suspenders", "joggers",
    "slip", "slips", "briefs", "cross", "flatus", "plus", "suit", "suits"
}

# Common plural-to-singular mappings in fashion
PLURAL_MAP = {
    "shoes": "shoe",
    "boots": "boot",
    "sandals": "sandal",
    "sneakers": "sneaker",
    "trainers": "trainer",
    "trousers": "trouser",
    "jackets": "jacket",
    "coats": "coat",
    "sweaters": "sweater",
    "shirts": "shirt",
    "skirts": "skirt",
    "tops": "top",
    "tees": "tee",
    "blouses": "blouse",
    "hoodies": "hoodie",
    "cardigans": "cardigan",
    "bags": "bag",
    "backpacks": "backpack",
    "belts": "belt",
    "scarves": "scarf",
    "scarfs": "scarf",
    "hats": "hat",
    "caps": "cap",
    "beanies": "beanie",
    "gloves": "glove",
    "mittens": "mitten",
    "socks": "sock",
    "bras": "bra",
    "earrings": "earring",
    "necklaces": "necklace",
    "rings": "ring",
    "bracelets": "bracelet",
    "watches": "watch",
    "umbrellas": "umbrella",
    "wallets": "wallet",
    "purses": "purse",
    "suits": "suit",
    "blazers": "blazer",
    "vests": "vest",
    "tunics": "tunic",
    "jumpsuits": "jumpsuit",
    "rompers": "romper",
    "swimsuits": "swimsuit",
    "bikinis": "bikini",
    "slippers": "slipper",
    "loafers": "loafer",
    "heels": "heel",
    "pumps": "pump",
    "flats": "flat",
    "mules": "mule",
    "clutches": "clutch",
    "ties": "tie",
    "bowties": "bowtie"
}


def strip_accents(text: str) -> str:
    """Normalize unicode and remove accent marks."""
    nfkc = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkc if not unicodedata.combining(c))


def normalize_compounds(text: str) -> str:
    """Normalize common fashion compound words, hyphens, and slashes."""
    # Normalize variants of T-shirt
    text = re.sub(r'\b(t[\s_-]*shirt|tshirt|tee[\s_-]*shirt)\b', 't-shirt', text, flags=re.IGNORECASE)
    # Common multi-word phrases to standard hyphenated or separated form
    text = re.sub(r'\btank[\s_-]*top\b', 'tank top', text, flags=re.IGNORECASE)
    text = re.sub(r'\bv[\s_-]*neck\b', 'v-neck', text, flags=re.IGNORECASE)
    text = re.sub(r'\bcrew[\s_-]*neck\b', 'crew neck', text, flags=re.IGNORECASE)
    text = re.sub(r'\bround[\s_-]*neck\b', 'round neck', text, flags=re.IGNORECASE)
    text = re.sub(r'\bhigh[\s_-]*waist(?:ed)?\b', 'high waist', text, flags=re.IGNORECASE)
    text = re.sub(r'\bwide[\s_-]*leg\b', 'wide leg', text, flags=re.IGNORECASE)
    text = re.sub(r'\bslim[\s_-]*fit\b', 'slim fit', text, flags=re.IGNORECASE)
    text = re.sub(r'\bskinny[\s_-]*fit\b', 'skinny fit', text, flags=re.IGNORECASE)
    text = re.sub(r'\brelaxed[\s_-]*fit\b', 'relaxed fit', text, flags=re.IGNORECASE)
    text = re.sub(r'\bregular[\s_-]*fit\b', 'regular fit', text, flags=re.IGNORECASE)
    text = re.sub(r'\bover[\s_-]*sized?\b', 'oversized', text, flags=re.IGNORECASE)
    text = re.sub(r'\blong[\s_-]*sleeve(?:d)?\b', 'long sleeve', text, flags=re.IGNORECASE)
    text = re.sub(r'\bshort[\s_-]*sleeve(?:d)?\b', 'short sleeve', text, flags=re.IGNORECASE)
    text = re.sub(r'\bflip[\s_-]*flops?\b', 'flip flops', text, flags=re.IGNORECASE)
    text = re.sub(r'\bpolo[\s_-]*shirt\b', 'polo shirt', text, flags=re.IGNORECASE)
    text = re.sub(r'\bnight[\s_-]*wear\b', 'nightwear', text, flags=re.IGNORECASE)
    text = re.sub(r'\bswim[\s_-]*wear\b', 'swimwear', text, flags=re.IGNORECASE)
    text = re.sub(r'\bunder[\s_-]*wear\b', 'underwear', text, flags=re.IGNORECASE)
    text = re.sub(r'\bactive[\s_-]*wear\b', 'activewear', text, flags=re.IGNORECASE)
    text = re.sub(r'\bsports?[\s_-]*wear\b', 'activewear', text, flags=re.IGNORECASE)
    text = re.sub(r'\blounge[\s_-]*wear\b', 'loungewear', text, flags=re.IGNORECASE)
    return text


def normalize_currency_and_numbers(text: str) -> str:
    """Normalize currency symbols, abbreviations like 2k, and commas in numbers."""
    # Replace ₹, Rs., Rs, INR with inr (word boundaries for alphabetic symbols)
    text = re.sub(r'(?:₹\s*|\b(?:rs\.?|inr)\s*)', 'inr ', text, flags=re.IGNORECASE)
    # Replace 2k, 1.5k, etc.
    def replace_k(m):
        val = float(m.group(1)) * 1000
        return f"{int(val)}"
    text = re.sub(r'\b(\d+(?:\.\d+)?)[kK]\b', replace_k, text)
    # Remove commas inside numbers: e.g. 1,500 -> 1500
    text = re.sub(r'(\d+),(\d{3})\b', r'\1\2', text)
    return text


def light_stem(word: str) -> str:
    """Conservatively stem singular/plural without hurting fashion terms."""
    w = word.lower()
    if w in STEM_EXCEPTIONS:
        return w
    if w in PLURAL_MAP:
        return PLURAL_MAP[w]
    # Simple rule-based fallback
    if len(w) > 4:
        if w.endswith('ies') and len(w) > 5 and not w.endswith(('eies', 'aies')):
            return w[:-3] + 'y'
        if w.endswith('es') and w[:-2].endswith(('ch', 'sh', 'ss', 'x', 'z')):
            if w == 'dresses':
                return 'dress'
            return w[:-2]
        if w.endswith('s') and not w.endswith(('ss', 'us', 'is', 'as')):
            return w[:-1]
    return w


def normalize_text(text: str) -> str:
    """Canonical text normalizer for both documents and queries."""
    if not text:
        return ""
    # Unicode NFKC
    text = unicodedata.normalize('NFKC', text)
    # Remove accents
    text = strip_accents(text)
    # Casefold
    text = text.casefold()
    # Normalize currency and numbers
    text = normalize_currency_and_numbers(text)
    # Normalize compound terms
    text = normalize_compounds(text)
    # Replace hyphens, slashes, apostrophes, ampersands with whitespace or preserve compounds
    text = text.replace('&', ' and ')
    text = re.sub(r"['’`]", "", text)
    # Replace punctuation with space
    text = re.sub(r'[^\w\s-]', ' ', text)
    # Hyphens within words
    text = re.sub(r'\s+', ' ', text).strip()
    return text


@lru_cache(maxsize=4096)
def tokenize_and_stem(text: str) -> tuple[str, ...]:
    """Normalize text into a tuple of stemmed tokens."""
    norm = normalize_text(text)
    raw_tokens = re.findall(r'[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*', norm)
    tokens = []
    for tok in raw_tokens:
        tok = tok.strip('-')
        if not tok:
            continue
        # Split hyphenated word into parts plus whole
        if '-' in tok:
            tokens.append(light_stem(tok))
            for part in tok.split('-'):
                if part:
                    tokens.append(light_stem(part))
        else:
            tokens.append(light_stem(tok))
    return tuple(tokens)


def extract_price_constraints(text: str) -> dict:
    """Extract price budgets from prose queries (e.g. under 2000, max 1500, between 500 and 1000)."""
    norm = normalize_text(text)
    constraints = {}

    # between X and Y
    m_between = re.search(r'\bbetween\s+(?:inr\s*)?(\d+)\s*(?:and|to)\s*(?:inr\s*)?(\d+)\b', norm)
    if m_between:
        p1 = float(m_between.group(1))
        p2 = float(m_between.group(2))
        constraints['min_price'] = min(p1, p2)
        constraints['max_price'] = max(p1, p2)
        return constraints

    # under / below / less than / up to / max / budget of X
    m_max = re.search(r'\b(?:under|below|less than|up to|max(?:imum)?|budget of|within|cheaper than)\s+(?:inr\s*)?(\d+)\b', norm)
    if m_max:
        constraints['max_price'] = float(m_max.group(1))

    # above / over / more than / min / at least X
    m_min = re.search(r'\b(?:above|over|more than|min(?:imum)?|at least|starting from)\s+(?:inr\s*)?(\d+)\b', norm)
    if m_min:
        constraints['min_price'] = float(m_min.group(1))

    return constraints
