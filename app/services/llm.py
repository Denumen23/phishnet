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

async def analyze_text_with_llm(text: str) -> dict:
    """
    Analyzes text for phishing using OpenRouter asynchronously.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_API_KEY_HERE":
        return {
            "status": "error",
            "message": "OpenRouter API key not configured."
        }

    model = "mistralai/mistral-7b-instruct:free"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a cybersecurity expert specializing in phishing detection. Analyze the following text from a webpage and determine if it is a phishing attempt. Your response should be a JSON object with two keys: 'result' ('safe' or 'phishing') and 'reasoning' (a brief explanation)."},
                        {"role": "user", "content": text}
                    ]
                }
            )
            response.raise_for_status()

            if 'application/json' in response.headers.get('Content-Type', ''):
                # The response from the LLM is a stringified JSON, so we need to parse it.
                llm_response_str = response.json()['choices'][0]['message']['content']
                return json.loads(llm_response_str)
            else:
                return {
                    "status": "error",
                    "message": "Received non-JSON response from OpenRouter."
                }

        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "message": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }
        except (KeyError, json.JSONDecodeError) as e:
            return {
                "status": "error",
                "message": f"Could not parse LLM response: {e}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


if __name__ == '__main__':
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

    print("\nAnalyzing with LLM...")
    analysis = asyncio.run(analyze_text_with_llm(extracted_text))
    print(analysis)
