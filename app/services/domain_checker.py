import json
from pathlib import Path
import tldextract

class DomainChecker:
    _instance = None
    _brand_domains = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DomainChecker, cls).__new__(cls)
            cls._instance._load_kb()
        return cls._instance

    def _load_kb(self):
        """Loads the brand knowledge base and builds the domain map."""
        kb_path = Path(__file__).parent / "data" / "brand_kb.json"
        try:
            with open(kb_path, 'r') as f:
                brand_data = json.load(f)

            for brand in brand_data:
                canonical_name = brand['name'].lower()
                self._brand_domains[canonical_name] = set(brand['domains'])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading brand knowledge base: {e}")
            self._brand_domains = {}

    def is_legitimate_domain(self, url: str, canonical_brand: str) -> bool:
        """
        Checks if the URL's domain is legitimate for the given brand.

        Args:
            url: The URL to check.
            canonical_brand: The canonical name of the brand.

        Returns:
            True if the domain is legitimate, False otherwise.
        """
        if not url or not canonical_brand:
            return False

        try:
            extracted = tldextract.extract(url)
            domain = extracted.top_domain_under_public_suffix

            legitimate_domains = self._brand_domains.get(canonical_brand.lower())

            if legitimate_domains and domain in legitimate_domains:
                return True
        except Exception as e:
            print(f"Error extracting domain from {url}: {e}")

        return False

# Singleton instance for easy access
domain_checker = DomainChecker()

if __name__ == '__main__':
    # Example Usage
    print("Testing Domain Checker...")
    print(f"Is login.microsoftonline.com a legitimate Microsoft domain? {domain_checker.is_legitimate_domain('https://login.microsoftonline.com/common', 'Microsoft')}")
    print(f"Is my-secure-login-microsoft.com a legitimate Microsoft domain? {domain_checker.is_legitimate_domain('http://my-secure-login-microsoft.com', 'Microsoft')}")
    print(f"Is google.com.phish.com a legitimate Google domain? {domain_checker.is_legitimate_domain('https://google.com.phish.com', 'Google')}")
    print(f"Is youtube.com a legitimate Google domain? {domain_checker.is_legitimate_domain('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'Google')}")
    print(f"Is amazon-aws.net a legitimate Amazon domain? {domain_checker.is_legitimate_domain('http://amazon-aws.net', 'Amazon')}")
