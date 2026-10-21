"""Conservative catalog-only spelling and typo correction."""
import collections
import json
from pathlib import Path


# Non-fashion, technical, scientific, or nonsense words that must never be corrected
NON_FASHION_WORDS = {
    "spaceship", "engine", "quantum", "algorithm", "blockchain", "cryptocurrency",
    "aerospace", "microprocessor", "semiconductor", "thermodynamics", "carburetor",
    "astronomy", "telescope", "constellation", "superconductor", "nanotechnology",
    "photosynthesis", "chlorophyll", "paleontology", "fossilization", "geology",
    "volcanology", "seismology", "meteorology", "stratosphere", "atmospheric",
    "chromatography", "spectroscopy", "metallurgy", "crystallography", "biotechnology",
    "microbiology", "epidemiology", "toxicology", "pharmacology", "neuroscience",
    "cybernetics", "cryptography", "telecommunications", "radar", "sonar",
    "pneumatic", "hydraulic", "combustion", "propulsion", "turbofan",
    "fuselage", "avionics", "altimeter", "tachometer", "gyroscope",
    "centrifuge", "synchrotron", "particle", "gravitational", "electromagnetic",
    "supernova", "exoplanet", "interstellar", "spacecraft", "satellite",
    "rover", "lander", "payload", "propellant", "suborbital",
    "orbital", "trajectory", "telemetry", "spectrometer", "magnetometer",
    "radiometer", "interferometer", "barometer", "anemometer", "hygrometer",
    "seismometer", "accelerometer", "inclinometer", "theodolite", "oscilloscope",
    "potentiometer", "galvanometer", "multimeter", "voltmeter", "ammeter",
    "ohmmeter", "pyrometer", "calorimeter", "densitometer", "refractometer",
    "polarimeter", "viscometer", "manometer", "chronometer", "audiometer",
    "spirometer", "dynamometer", "ergometer", "glucometer",
    "banana", "fruit", "grocery", "groceries", "food", "airline", "flight",
    "ticket", "tickets", "automotive", "car", "real", "estate", "apartment",
    "rent", "television", "tv", "microchip", "processor", "laptop", "smartphone",
    "computer", "mining", "rig", "screen", "thruster", "seismograph", "detector", "coil", "test"
}


class SpellingCorrector:
    def __init__(self, vocab_frequencies: dict[str, int] = None):
        self.vocab = vocab_frequencies or {}
        # Precompute character n-grams for candidate pre-filtering
        self.trigram_index = collections.defaultdict(set)
        for word in self.vocab:
            if len(word) >= 3:
                padded = f"^{word}$"
                for i in range(len(padded) - 2):
                    self.trigram_index[padded[i:i+3]].add(word)

    @classmethod
    def from_products(cls, products: list[dict], min_freq: int = 5):
        """Build catalog vocabulary from real products."""
        import re
        from seo.normalize import normalize_text
        freq = collections.Counter()
        for p in products:
            text = " ".join([
                p.get("name") or "",
                p.get("product_type") or "",
                p.get("category") or "",
                p.get("color") or "",
                p.get("pattern") or "",
                p.get("audience") or ""
            ])
            tokens = set(re.findall(r'\b[a-z]{3,}\b', normalize_text(text)))
            for tok in tokens:
                freq[tok] += 1

        filtered = {k: v for k, v in freq.items() if v >= min_freq}
        return cls(filtered)

    @staticmethod
    def edit_distance_1(word: str) -> set[str]:
        """Generate all edits at distance 1."""
        letters = 'abcdefghijklmnopqrstuvwxyz'
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [L + R[1:] for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
        inserts = [L + c + R for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    @staticmethod
    def edit_distance(s1: str, s2: str) -> int:
        """Standard Levenshtein distance."""
        if len(s1) < len(s2):
            return SpellingCorrector.edit_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row
        return prev_row[-1]

    def correct_token(self, token: str) -> tuple[str, bool]:
        """Conservatively correct a single token if it is a plausible typo of a catalog term.
        Returns (corrected_token, was_corrected).
        Never corrects out-of-catalog words that are nonsense or non-fashion.
        """
        tok = token.lower()
        if tok in self.vocab or tok in NON_FASHION_WORDS:
            return tok, False

        # Only correct words of length >= 4
        if len(tok) < 4:
            return tok, False

        # Check distance 1 candidates
        candidates_d1 = [
            w for w in self.edit_distance_1(tok)
            if w in self.vocab and w[0] == tok[0] and abs(len(w) - len(tok)) <= 1 and self.vocab[w] >= 20
        ]
        if candidates_d1:
            best = max(candidates_d1, key=lambda w: self.vocab[w])
            return best, True

        # Check distance 2 candidates ONLY for longer words (length >= 6)
        if len(tok) >= 6:
            padded = f"^{tok}$"
            tok_tgs = set(padded[i:i+3] for i in range(len(padded) - 2))
            d2_matches = []
            for w in self.vocab:
                if abs(len(w) - len(tok)) <= 1 and w[0] == tok[0] and self.vocab[w] >= 40:
                    w_padded = f"^{w}$"
                    w_tgs = set(w_padded[i:i+3] for i in range(len(w_padded) - 2))
                    if len(tok_tgs & w_tgs) >= 3 and self.edit_distance(tok, w) <= 2:
                        d2_matches.append(w)

            if d2_matches:
                best = max(d2_matches, key=lambda w: self.vocab[w])
                return best, True

        # If not a verified fashion typo, keep original as-is
        return tok, False

    def correct_query(self, query_tokens: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
        """Correct typos in a list of query tokens. Returns (new_tokens, list_of_corrections)."""
        corrected = []
        corrections = []
        for tok in query_tokens:
            c, changed = self.correct_token(tok)
            corrected.append(c)
            if changed:
                corrections.append((tok, c))
        return corrected, corrections

    def save(self, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.vocab, f, indent=2)
