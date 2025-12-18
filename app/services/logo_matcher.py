import cv2
import numpy as np
import os

def find_logo(screenshot_path: str, logo_dir: str = "app/services/data/logos") -> str | None:
    """
    Finds a matching logo from the logo directory in the given screenshot using ORB.
    """
    try:
        screenshot = cv2.imread(screenshot_path, 0)
        if screenshot is None:
            raise FileNotFoundError(f"Could not read screenshot image at {screenshot_path}")
    except Exception as e:
        print(f"Error reading screenshot: {e}")
        return None

    orb = cv2.ORB_create(nfeatures=1000)
    kp1, des1 = orb.detectAndCompute(screenshot, None)

    if des1 is None:
        print("Could not find features in the screenshot.")
        return None

    for logo_file in os.listdir(logo_dir):
        logo_path = os.path.join(logo_dir, logo_file)
        try:
            logo = cv2.imread(logo_path, 0)
            if logo is None:
                raise FileNotFoundError(f"Could not read logo image at {logo_path}")
        except Exception as e:
            print(f"Warning: {e}")
            continue

        kp2, des2 = orb.detectAndCompute(logo, None)

        if des2 is None:
            print(f"Could not find features in logo {logo_file}.")
            continue

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        if des1.dtype != des2.dtype:
            print(f"Descriptor types for screenshot and {logo_file} do not match.")
            continue

        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)

        # Use a ratio test or a fixed number of good matches
        good_matches = [m for m in matches if m.distance < 75]

        print(f"Found {len(good_matches)} good matches for {logo_file}.")

        if len(good_matches) > 10:  # Threshold for a good match
            return logo_file.split('.')[0]

    return None

if __name__ == '__main__':
    import asyncio
    from fetch import get_screenshot

    test_url = "https://www.google.com"
    screenshot_file = "google_screenshot.png"

    print("Taking screenshot...")
    asyncio.run(get_screenshot(test_url, screenshot_file))
    print("Screenshot taken.")

    print("Finding logo...")
    matched_brand = find_logo(screenshot_file)
    if matched_brand:
        print(f"Logo matched: {matched_brand}")
    else:
        print("No logo matched.")
