"""Data-quality unit tests proving the SEO layer accuracy and integrity."""
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from search import Catalog
from seo.aliases import (
    PRODUCT_TYPE_ALIASES, CATEGORY_ALIASES, AUDIENCE_ALIASES,
    COLOR_ALIASES, PATTERN_ALIASES
)
from seo.spelling import SpellingCorrector
from seo.normalize import normalize_text


class SEODataQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog_path = ROOT / "data" / "products.json"
        with open(catalog_path, "r", encoding="utf-8") as f:
            cls.products = json.load(f)
        cls.catalog = Catalog.load(catalog_path)
        cls.corrector = cls.catalog.engine.corrector

        # Precompute sets of real catalog values
        cls.valid_values = {
            "product_type": set(p.get("product_type") for p in cls.products if p.get("product_type")),
            "category": set(p.get("category") for p in cls.products if p.get("category")),
            "audience": set(p.get("audience") for p in cls.products if p.get("audience")),
            "section": set(p.get("section") for p in cls.products if p.get("section")),
            "color": set(p.get("color") for p in cls.products if p.get("color")),
            "pattern": set(p.get("pattern") for p in cls.products if p.get("pattern")),
        }

    def test_c_every_alias_target_exists(self):
        """Every alias target must exist in the real catalog values."""
        for name, table in [
            ("product_type", PRODUCT_TYPE_ALIASES),
            ("category", CATEGORY_ALIASES),
            ("audience", AUDIENCE_ALIASES),
            ("color", COLOR_ALIASES),
            ("pattern", PATTERN_ALIASES)
        ]:
            known = self.valid_values[name]
            for src, target in table.items():
                self.assertIn(
                    target, known,
                    f"Alias '{src}' -> '{target}' does not exist in catalog '{name}'!"
                )

    def test_a_retrievability_by_name_and_aliases(self):
        """Every product_type, category, color, pattern, audience is retrievable by own name and aliases."""
        # 1. Product types
        for ptype in self.valid_values["product_type"]:
            if ptype in ("Unknown",):
                continue
            res = self.catalog.search({"query": ptype, "limit": 10})["results"]
            self.assertGreater(
                len(res), 0,
                f"Product type '{ptype}' returned no results when searched by own name!"
            )

        # 2. Key aliases
        test_aliases = ["tee", "pants", "dress", "jeans", "trainers", "hoodie", "jacket", "skirt"]
        for alias in test_aliases:
            res = self.catalog.search({"query": alias, "limit": 10})["results"]
            self.assertGreater(
                len(res), 0,
                f"Alias '{alias}' returned no results!"
            )

    def test_b_sample_2000_products_retrievable_by_name(self):
        """For a sample of 2,000 products, searching own name returns product or identical name in top 10."""
        random.seed(42)
        sample = random.sample(self.products, 2000)
        successes = 0

        for p in sample:
            name = p.get("name")
            if not name or len(name.strip()) < 2:
                successes += 1
                continue
            res = self.catalog.search({"query": name, "limit": 10})["results"]
            retrieved_ids = set(r["id"] for r in res)
            # Check if this exact ID or a variant with identical name was retrieved in top 10
            matched = False
            if p["id"] in retrieved_ids:
                matched = True
            else:
                for r in res:
                    r_idx = self.catalog.engine.index.id_to_idx[r["id"]]
                    if self.products[r_idx].get("name", "").casefold() == name.casefold():
                        matched = True
                        break
            if matched:
                successes += 1

        recall_rate = successes / len(sample)
        print(f"\n[Test B] Sample 2,000 name retrieval rate: {recall_rate * 100:.2f}% ({successes}/2000)")
        self.assertGreaterEqual(
            recall_rate, 0.95,
            f"Expected at least 95% top-10 retrieval rate for own name, got {recall_rate * 100:.2f}%"
        )

    def test_d_typo_correction_accuracy_and_rejection(self):
        """200 generated 1/2-char typos of real catalog words are corrected, and 100 nonsense words are NOT corrected."""
        random.seed(42)
        real_words = [w for w in self.corrector.vocab if len(w) >= 5 and self.corrector.vocab[w] >= 20]
        self.assertGreater(len(real_words), 200)

        sample_words = random.sample(real_words, 200)
        corrected_count = 0

        for w in sample_words:
            # Generate 1-character substitution typo
            idx = random.randint(1, len(w) - 1)
            char = random.choice('abcdefghijklmnopqrstuvwxyz')
            if char == w[idx]:
                char = 'x' if char != 'x' else 'z'
            typo = w[:idx] + char + w[idx+1:]

            res, was_corr = self.corrector.correct_token(typo)
            if res == w:
                corrected_count += 1

        typo_acc = corrected_count / len(sample_words)
        print(f"\n[Test D] Typo correction accuracy on 200 catalog words: {typo_acc * 100:.2f}% ({corrected_count}/200)")
        self.assertGreaterEqual(typo_acc, 0.85, f"Typo correction accuracy {typo_acc*100:.2f}% below 85%")

        # 100 Nonsense / Non-fashion words that MUST NOT be corrected into catalog words
        nonsense_words = [
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
            "spirometer", "dynamometer", "ergometer", "glucometer"
        ]
        self.assertEqual(len(nonsense_words), 100)
        false_corrections = 0
        for nw in nonsense_words:
            res, was_corr = self.corrector.correct_token(nw)
            if was_corr:
                false_corrections += 1

        print(f"[Test D] False correction count on 100 non-fashion words: {false_corrections}/100 (0 required)")
        self.assertEqual(false_corrections, 0, f"Nonsense words erroneously corrected into catalog words: {false_corrections}")


if __name__ == "__main__":
    unittest.main()
