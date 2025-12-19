from PIL import Image
import pytesseract
import json
from pathlib import Path

class OcrBrandDetector:
    _instance = None
    _brand_aliases = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OcrBrandDetector, cls).__new__(cls)
            cls._instance._load_kb()
        return cls._instance

    def _load_kb(self):
        """Loads brand aliases from the knowledge base."""
        kb_path = Path(__file__).parent / "data" / "brand_kb.json"
        try:
            with open(kb_path, 'r') as f:
                brand_data = json.load(f)

            for brand in brand_data:
                for alias in brand['aliases']:
                    self._brand_aliases.add(alias.lower())
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading brand knowledge base: {e}")
            self._brand_aliases = set()

    def find_brand_in_image(self, screenshot_path: str) -> str | None:
        """
        Performs OCR on an image and checks for the presence of known brand aliases.

        Args:
            screenshot_path: The path to the screenshot image.

        Returns:
            The first brand alias found in the image, or None.
        """
        try:
            # Perform OCR on the image to get all text
            image_text = pytesseract.image_to_string(Image.open(screenshot_path)).lower()

            # Check if any of the known brand aliases are in the OCR text
            for alias in self._brand_aliases:
                if alias in image_text:
                    print(f"Found brand alias via OCR: {alias}")
                    return alias
        except Exception as e:
            print(f"Error during OCR processing: {e}")

        return None

# Singleton instance
ocr_brand_detector = OcrBrandDetector()

if __name__ == '__main__':
    # This test requires a screenshot to be present
    # As a simple test, we assume a file 'google_test.png' exists
    from app.services.fetch import get_screenshot
    import asyncio

    async def test_ocr_detector():
        # Positive case
        url = "https://www.google.com"
        screenshot_file = "google_ocr_test.png"
        print(f"Taking screenshot of {url}...")
        await get_screenshot(url, screenshot_file)
        print("Finding brand in image via OCR...")
        brand = ocr_brand_detector.find_brand_in_image(screenshot_file)
        if brand:
            print(f"SUCCESS: Found brand '{brand}' on {url}")
        else:
            print(f"FAILURE: Did not find a brand on {url}")

    asyncio.run(test_ocr_detector())
