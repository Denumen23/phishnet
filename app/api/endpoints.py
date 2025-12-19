from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.fetch import get_html, get_screenshot
from app.services.logo_matcher import ocr_brand_detector
from app.services.llm import extract_text_from_html, is_credential_page_llm, identify_brand_llm
from app.services.brand_normalizer import brand_normalizer
from app.services.domain_checker import domain_checker
import os
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

router = APIRouter()

class AnalyzeRequest(BaseModel):
    url: str

class LLMAnalysis(BaseModel):
    is_credential_page: bool
    identified_brand_alias: str | None
    canonical_brand: str | None

class ImageAnalysis(BaseModel):
    found_brand_alias: str | None
    canonical_brand: str | None

class DomainAnalysis(BaseModel):
    is_legitimate: bool | None

class AnalyzeResponse(BaseModel):
    url: str
    phishing_score: float
    llm_analysis: LLMAnalysis
    image_analysis: ImageAnalysis
    domain_analysis: DomainAnalysis

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url(request: AnalyzeRequest):
    url = request.url
    logging.info(f"Starting analysis for URL: {url}")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        screenshot_path = temp_file.name

    try:
        logging.info("Fetching HTML and taking screenshot...")
        html_content = await get_html(url)
        if not html_content:
            logging.error("Failed to fetch HTML content.")
            raise HTTPException(status_code=400, detail="Could not fetch HTML from the URL.")

        try:
            await get_screenshot(url, screenshot_path)
            logging.info(f"Screenshot saved to {screenshot_path}")
        except Exception as e:
            logging.error(f"Failed to take screenshot: {e}")
            raise HTTPException(status_code=500, detail=f"Error during page screenshot: {e}")

        text = extract_text_from_html(html_content)

        logging.info("Step 1: Checking for credential-requiring page (CRP)...")
        is_crp = await is_credential_page_llm(text)
        logging.info(f"Is CRP? {is_crp}")

        score = 0
        identified_brand_alias_llm = None
        canonical_brand_llm = None
        is_legitimate_domain = None

        if is_crp:
            score += 20
            logging.info("Step 2a: CRP detected. Identifying brand from text...")
            identified_brand_alias_llm = await identify_brand_llm(text)
            logging.info(f"LLM identified brand alias: '{identified_brand_alias_llm}'")
            if identified_brand_alias_llm:
                canonical_brand_llm = brand_normalizer.normalize_brand(identified_brand_alias_llm)
                logging.info(f"Normalized to canonical brand: '{canonical_brand_llm}'")

        logging.info("Step 2b: Identifying brand from image via OCR...")
        found_brand_alias_ocr = ocr_brand_detector.find_brand_in_image(screenshot_path)
        logging.info(f"OCR found brand alias: '{found_brand_alias_ocr}'")
        canonical_brand_ocr = None
        if found_brand_alias_ocr:
            canonical_brand_ocr = brand_normalizer.normalize_brand(found_brand_alias_ocr)
            logging.info(f"Normalized to canonical brand: '{canonical_brand_ocr}'")

        final_canonical_brand = canonical_brand_llm or canonical_brand_ocr
        logging.info(f"Final canonical brand for domain check: '{final_canonical_brand}'")

        if is_crp and final_canonical_brand:
            logging.info("Step 3: Performing domain legitimacy check...")
            is_legitimate_domain = domain_checker.is_legitimate_domain(url, final_canonical_brand)
            logging.info(f"Is domain legitimate for '{final_canonical_brand}'? {is_legitimate_domain}")
            if not is_legitimate_domain:
                score = 95
            else:
                score = 5

        final_score = min(score, 100)
        logging.info(f"Final phishing score for {url}: {final_score}")

        return AnalyzeResponse(
            url=url,
            phishing_score=final_score,
            llm_analysis=LLMAnalysis(
                is_credential_page=is_crp,
                identified_brand_alias=identified_brand_alias_llm,
                canonical_brand=canonical_brand_llm
            ),
            image_analysis=ImageAnalysis(
                found_brand_alias=found_brand_alias_ocr,
                canonical_brand=canonical_brand_ocr
            ),
            domain_analysis=DomainAnalysis(is_legitimate=is_legitimate_domain)
        )
    finally:
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
            logging.info(f"Cleaned up temporary file: {screenshot_path}")
