import json
from pathlib import Path

class BrandNormalizer:
    _instance = None
    _alias_map = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrandNormalizer, cls).__new__(cls)
            cls._instance._load_kb()
        return cls._instance

    def _load_kb(self):
        """Loads the brand knowledge base and builds the alias map."""
        kb_path = Path(__file__).parent / "data" / "brand_kb.json"
        try:
            with open(kb_path, 'r') as f:
                brand_data = json.load(f)

            for brand in brand_data:
                canonical_name = brand['name']
                for alias in brand['aliases']:
                    self._alias_map[alias.lower()] = canonical_name
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading brand knowledge base: {e}")
            # In a real application, you might want to raise an exception
            # or handle this more gracefully.
            self._alias_map = {}

    def normalize_brand(self, brand_alias: str) -> str | None:
        """
        Normalizes a brand alias to its canonical name.

        Args:
            brand_alias: The brand alias to normalize.

        Returns:
            The canonical brand name, or None if no match is found.
        """
        if not brand_alias:
            return None
        return self._alias_map.get(brand_alias.lower())

# Singleton instance for easy access
brand_normalizer = BrandNormalizer()

if __name__ == '__main__':
    # Example Usage
    print("Testing Brand Normalizer...")
    print(f"Mapping for 'Google': {brand_normalizer.normalize_brand('Google')}")
    print(f"Mapping for 'ms': {brand_normalizer.normalize_brand('ms')}")
    print(f"Mapping for 'Amazon Web Services': {brand_normalizer.normalize_brand('Amazon Web Services')}")
    print(f"Mapping for 'UnknownBrand': {brand_normalizer.normalize_brand('UnknownBrand')}")
    print(f"Mapping for 'gmail': {brand_normalizer.normalize_brand('gmail')}")
