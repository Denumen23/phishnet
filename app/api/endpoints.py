from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
from app.services.fetch import get_html, get_screenshot
from app.services.logo_matcher import find_logo
from app.services.llm import extract_text_from_html, analyze_text_with_llm
import json
import os
import tempfile

router = APIRouter()

class AnalyzeRequest(BaseModel):
    url: str

class AnalyzeResponse(BaseModel):
    url: str
    phishing_score: float
    matched_brand: str | None
    llm_analysis: dict

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url(request: AnalyzeRequest):
    url = request.url

    # Create a temporary file for the screenshot
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        screenshot_path = temp_file.name

    try:
        # 1. Fetch HTML and take a screenshot
        html_content = await get_html(url)
        if not html_content:
            raise HTTPException(status_code=400, detail="Could not fetch HTML from the URL.")

        try:
            await get_screenshot(url, screenshot_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error during page screenshot: {e}")

        # 2. Match logo
        matched_brand = find_logo(screenshot_path)

        # 3. Analyze text with LLM
        text = extract_text_from_html(html_content)
        llm_analysis = await analyze_text_with_llm(text)

        # Check for error from LLM analysis
        if llm_analysis.get("status") == "error":
            raise HTTPException(status_code=500, detail=llm_analysis.get("message"))

        # 4. Calculate phishing score (simple logic for MVP)
        score = 0
        if llm_analysis.get('result') == 'phishing':
            score += 80
        if matched_brand:
            score += 10

        return AnalyzeResponse(
            url=url,
            phishing_score=score,
            matched_brand=matched_brand,
            llm_analysis=llm_analysis
        )
    finally:
        # Clean up the temporary screenshot file
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
