from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.fetch import get_html, get_screenshot
from app.services.logo_matcher import find_logo
from app.services.llm import extract_text_from_html, is_credential_page_llm, identify_brand_llm
import os
import tempfile

router = APIRouter()

class AnalyzeRequest(BaseModel):
    url: str

class LLMAnalysis(BaseModel):
    is_credential_page: bool
    identified_brand: str | None

class AnalyzeResponse(BaseModel):
    url: str
    phishing_score: float
    matched_brand_logo: str | None
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
        identified_brand_by_llm = None

        if is_crp:
            # If it's a credential page, it's inherently more suspicious
            score += 40
            identified_brand_by_llm = await identify_brand_llm(text)
            if identified_brand_by_llm:
                # Impersonating a specific brand is a strong phishing signal
                score += 50

        matched_brand_logo = find_logo(screenshot_path)
        if matched_brand_logo:
            # Finding a logo of a known brand increases the score
            score += 10
            # A small bonus if the logo and text agree
            if identified_brand_by_llm and matched_brand_logo.lower() in identified_brand_by_llm.lower():
                score += 10

        return AnalyzeResponse(
            url=url,
            phishing_score=min(score, 100),
            matched_brand_logo=matched_brand_logo,
            llm_analysis=LLMAnalysis(
                is_credential_page=is_crp,
                identified_brand=identified_brand_by_llm
            )
        )
    finally:
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
