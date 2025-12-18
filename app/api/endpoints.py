from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.fetch import get_html, get_screenshot
from app.services.logo_matcher import find_logo
from app.services.llm import extract_text_from_html, is_credential_page_llm, identify_brand_llm
from app.services.brand_normalizer import brand_normalizer
import os
import tempfile

router = APIRouter()

class AnalyzeRequest(BaseModel):
    url: str

class LLMAnalysis(BaseModel):
    is_credential_page: bool
    identified_brand_alias: str | None
    canonical_brand: str | None

class AnalyzeResponse(BaseModel):
    url: str
    phishing_score: float
    matched_brand_logo_alias: str | None
    canonical_brand_logo: str | None
    llm_analysis: LLMAnalysis

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

        if is_crp:
            score += 40
            identified_brand_alias = await identify_brand_llm(text)
            if identified_brand_alias:
                canonical_brand_llm = brand_normalizer.normalize_brand(identified_brand_alias)
                if canonical_brand_llm:
                    score += 50

        matched_brand_logo_alias = find_logo(screenshot_path)
        canonical_brand_logo = None
        if matched_brand_logo_alias:
            canonical_brand_logo = brand_normalizer.normalize_brand(matched_brand_logo_alias)
            if canonical_brand_logo:
                score += 10
                if canonical_brand_llm and canonical_brand_logo == canonical_brand_llm:
                    score += 10

        return AnalyzeResponse(
            url=url,
            phishing_score=min(score, 100),
            matched_brand_logo_alias=matched_brand_logo_alias,
            canonical_brand_logo=canonical_brand_logo,
            llm_analysis=LLMAnalysis(
                is_credential_page=is_crp,
                identified_brand_alias=identified_brand_alias,
                canonical_brand=canonical_brand_llm
            )
        )
    finally:
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
