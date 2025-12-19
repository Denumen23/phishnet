import httpx
from bs4 import BeautifulSoup
from app.core.config import OPENROUTER_API_KEY, OPENROUTER_MODEL_NAME
import json
import asyncio
import logging

def get_relevant_content_from_html(html: str) -> str:
    """
    Extracts relevant content from HTML for LLM analysis.
    It prioritizes returning the full HTML of <form> tags if they exist.
    If not, it extracts clean text from the entire page as a fallback.
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script and style elements to clean up the source
    for script in soup(["script", "style"]):
        script.extract()

    forms = soup.find_all('form')
    if forms:
        # If forms are found, return their full HTML content
        return "\n".join(str(form) for form in forms)
    else:
        # Fallback: get clean text from the entire body
        text = soup.get_text(separator=' ')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return '\n'.join(chunk for chunk in chunks if chunk)

def has_form_with_input(html: str) -> bool:
    """
    Deterministically checks if the HTML contains a <form> with at least one <input>.
    """
    soup = BeautifulSoup(html, 'html.parser')
    forms = soup.find_all('form')
    for form in forms:
        if form.find('input'):
            return True
    return False

def extract_text_from_html_content(html: str) -> str:
    """
    Extracts plain text from an HTML string.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return '\n'.join(chunk for chunk in chunks if chunk)

async def _query_openrouter(messages: list) -> dict:
    """
    Helper function to query the OpenRouter API.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_API_KEY_HERE":
        return {"status": "error", "message": "OpenRouter API key not configured."}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": OPENROUTER_MODEL_NAME, "messages": messages}
            )
            response.raise_for_status()

            if 'application/json' in response.headers.get('Content-Type', ''):
                llm_response_str = response.json()['choices'][0]['message']['content']
                return json.loads(llm_response_str)
            else:
                return {"status": "error", "message": "Received non-JSON response from OpenRouter."}
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"}
        except (KeyError, json.JSONDecodeError) as e:
            return {"status": "error", "message": f"Could not parse LLM response: {e}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Load the prompt from the markdown file
with open('app/services/data/CRP.md', 'r') as f:
    CRP_PROMPT = f.read()

async def is_credential_page_llm(form_html: str) -> bool:
    """
    Analyzes the HTML of a form to determine if it's a credential-requiring page (CRP).
    """
    logging.info(f"Sending the following HTML to the LLM for CRP analysis:\n{form_html}")
    messages = [
        {"role": "system", "content": CRP_PROMPT},
        {"role": "user", "content": form_html}
    ]
    response = await _query_openrouter(messages)
    return response.get('is_credential_page', False)

async def identify_brand_llm(text: str) -> str | None:
    """
    Identifies the brand being impersonated on a credential-requiring page.
    """
    messages = [
        {"role": "system", "content": "You are a brand detection assistant. Analyze the text from a login page. Identify the primary brand being represented or impersonated. The brand could be a company (e.g., 'Microsoft'), a service (e.g., 'Gmail'), or a product (e.g., 'Office 350'). Respond with a JSON object with a single key: 'brand_name'. If no specific brand can be identified, return 'Unknown'."},
        {"role": "user", "content": text}
    ]
    response = await _query_openrouter(messages)
    brand_name = response.get('brand_name')
    return brand_name if brand_name and brand_name.lower() != 'unknown' else None
