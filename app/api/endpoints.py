from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.fetch import get_html, get_screenshot
from app.services.logo_matcher import find_logo
from app.services.llm import extract_text_from_html, is_credential_page_llm, identify_brand_llm
from app.services.brand_normalizer import brand_normalizer
from app.services.domain_checker import domain_checker
import os
import tempfile

router = APIRouter()

class AnalyzeRequest(BaseModel):
    url: str

class LLMAnalysis(BaseModel):
    is_credential_page: bool
    identified_brand_alias: str | None
    canonical_brand: str | None

class DomainAnalysis(BaseModel):
    is_legitimate: bool | None

class AnalyzeResponse(BaseModel):
    url: str
    phishing_score: float
    matched_brand_logo_alias: str | None
    canonical_brand_logo: str | None
    llm_analysis: LLMAnalysis
    domain_analysis: DomainAnalysis

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url(request: AnalyzeRequest):
    url = request.url

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        screenshot_path = temp_file.name

    try:
        html_content = await get_html(url)
        if not html_content:
            raise HTTPException(status_code=400, detail="Could not fetch HTML from the URL.")

        try:
            await get_screenshot(url, screenshot_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error during page screenshot: {e}")

        text = extract_text_from_html(html_content)
        is_crp = await is_credential_page_llm(text)

        score = 0
        identified_brand_alias = None
        canonical_brand_llm = None
        is_legitimate_domain = None

        if is_crp:
            score += 20 # Base score for being a credential page
            identified_brand_alias = await identify_brand_llm(text)
            if identified_brand_alias:
                canonical_brand_llm = brand_normalizer.normalize_brand(identified_brand_alias)

        matched_brand_logo_alias = find_logo(screenshot_path)
        canonical_brand_logo = None
        if matched_brand_logo_alias:
            canonical_brand_logo = brand_normalizer.normalize_brand(matched_brand_logo_alias)

        # Determine the final canonical brand from either source
        final_canonical_brand = canonical_brand_llm or canonical_brand_logo

        if is_crp and final_canonical_brand:
            is_legitimate_domain = domain_checker.is_legitimate_domain(url, final_canonical_brand)
            if not is_legitimate_domain:
                # This is the strongest signal for phishing
                score = 95
            else:
                # If the domain is legitimate, it's very unlikely to be phishing
                score = 5

        return AnalyzeResponse(
            url=url,
            phishing_score=min(score, 100),
            matched_brand_logo_alias=matched_brand_logo_alias,
            canonical_brand_logo=canonical_brand_logo,
            llm_analysis=LLMAnalysis(
                is_credential_page=is_crp,
                identified_brand_alias=identified_brand_alias,
                canonical_brand=canonical_brand_llm
            ),
            domain_analysis=DomainAnalysis(is_legitimate=is_legitimate_domain)
        )
    finally:
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
