import httpx
from bs4 import BeautifulSoup
from app.core.config import OPENROUTER_API_KEY
import json
import asyncio

def extract_text_from_html(html: str) -> str:
    """
    Extracts visible text from HTML content.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

async def _query_openrouter(messages: list) -> dict:
    """
    Helper function to query the OpenRouter API.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_API_KEY_HERE":
        return {"status": "error", "message": "OpenRouter API key not configured."}

    model = "mistralai/mistral-7b-instruct:free"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages}
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

async def is_credential_page_llm(text: str) -> bool:
    """
    Determines if the text content suggests a credential-requiring page (CRP).
    """
    messages = [
        {"role": "system", "content": "You are a cybersecurity assistant. Analyze the following text from a webpage. Your task is to determine if it's a login page, a sign-in form, or a page that explicitly asks for a password, security code, or other credentials. Respond with a JSON object with a single boolean key: 'is_credential_page'."},
        {"role": "user", "content": text}
    ]
    response = await _query_openrouter(messages)
    return response.get('is_credential_page', False)

async def identify_brand_llm(text: str) -> str | None:
    """
    Identifies the brand being impersonated on a credential-requiring page.
    """
    messages = [
        {"role": "system", "content": "You are a brand detection assistant. Analyze the text from a login page. Identify the primary brand being represented or impersonated. The brand could be a company (e.g., 'Microsoft'), a service (e.g., 'Gmail'), or a product (e.g., 'Office 365'). Respond with a JSON object with a single key: 'brand_name'. If no specific brand can be identified, return 'Unknown'."},
        {"role": "user", "content": text}
    ]
    response = await _query_openrouter(messages)
    brand_name = response.get('brand_name')
    return brand_name if brand_name and brand_name.lower() != 'unknown' else None

async def main():
    # Example usage
    sample_html = """
    <html>
        <body>
            <h1>Sign in to your account</h1>
            <p>We've detected suspicious activity on your Microsoft account. Please verify your identity to avoid your account being locked.</p>
            <form>
                <label>Email:</label><br>
                <input type="text"><br>
                <label>Password:</label><br>
                <input type="password"><br>
                <input type="submit" value="Login to Microsft">
            </form>
        </body>
    </html>
    """

    extracted_text = extract_text_from_html(sample_html)
    print("Extracted Text:")
    print(extracted_text)

    print("\nChecking if it's a credential page...")
    is_crp = await is_credential_page_llm(extracted_text)
    print(f"Is Credential Page: {is_crp}")

    if is_crp:
        print("\nIdentifying brand...")
        brand = await identify_brand_llm(extracted_text)
        print(f"Identified Brand: {brand}")

if __name__ == '__main__':
    asyncio.run(main())
