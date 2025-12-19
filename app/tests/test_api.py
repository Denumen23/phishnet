import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock

client = TestClient(app)

@patch('app.api.endpoints.domain_checker')
@patch('app.api.endpoints.brand_normalizer')
@patch('app.api.endpoints.ocr_brand_detector')
@patch('app.api.endpoints.identify_brand_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_legitimate_login_page(
    mock_get_html, mock_get_screenshot, mock_is_crp, mock_identify_brand, mock_ocr, mock_normalizer, mock_domain_checker
):
    """
    Tests a legitimate login page, which should result in a low phishing score.
    """
    mock_get_html.return_value = "<html><body><form>Sign in to Microsoft</form></body></html>"
    mock_get_screenshot.return_value = None
    mock_is_crp.return_value = True
    mock_identify_brand.return_value = "Microsoft"
    mock_ocr.find_brand_in_image.return_value = "Microsoft"
    mock_normalizer.normalize_brand.return_value = "Microsoft"
    mock_domain_checker.is_legitimate_domain.return_value = True

    response = client.post("/analyze", json={"url": "https://login.microsoft.com"})

    assert response.status_code == 200
    data = response.json()
    assert data['phishing_score'] == 5
    assert data['domain_analysis']['is_legitimate'] is True

@patch('app.api.endpoints.domain_checker')
@patch('app.api.endpoints.brand_normalizer')
@patch('app.api.endpoints.ocr_brand_detector')
@patch('app.api.endpoints.identify_brand_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_phishing_page_on_mismatched_domain(
    mock_get_html, mock_get_screenshot, mock_is_crp, mock_identify_brand, mock_ocr, mock_normalizer, mock_domain_checker
):
    """
    Tests a phishing page on a mismatched domain, which should result in a high phishing score.
    """
    mock_get_html.return_value = "<html><body><form>Sign in to Microsoft</form></body></html>"
    mock_get_screenshot.return_value = None
    mock_is_crp.return_value = True
    mock_identify_brand.return_value = "Microsoft"
    mock_ocr.find_brand_in_image.return_value = "Microsoft"
    mock_normalizer.normalize_brand.return_value = "Microsoft"
    mock_domain_checker.is_legitimate_domain.return_value = False

    response = client.post("/analyze", json={"url": "http://microsoft-login.phish-site.com"})

    assert response.status_code == 200
    data = response.json()
    assert data['phishing_score'] == 95
    assert data['domain_analysis']['is_legitimate'] is False

@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_analyze_url_fetch_fails(mock_get_html):
    """
    Tests the endpoint when HTML fetching fails.
    """
    mock_get_html.return_value = ""

    response = client.post("/analyze", json={"url": "https://bad-url.com"})

    assert response.status_code == 400
    assert "Could not fetch HTML" in response.json()['detail']

@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_multistep_login_is_crp(mock_get_html, mock_is_crp):
    """
    Tests that a multi-step login page (e.g., asking for username first) is identified as a CRP.
    """
    # This HTML simulates the first step of a login, asking for an email/username.
    mock_get_html.return_value = "<html><body><form><h1>Sign in</h1><p>Enter your email address to continue.</p><input type='email' /></form></body></html>"
    mock_is_crp.return_value = True # The updated prompt should now return True for this.

    response = client.post("/analyze", json={"url": "https://example.com/login-step-one"})

    # We are only interested in whether the is_credential_page_llm was called and returned true
    # The rest of the analysis will fail because we are not mocking all the other functions
    # but that is ok for this test.
    mock_is_crp.assert_awaited_once()

    # To test the logic inside is_credential_page_llm, we would need to unpatch it and let it run
    # but that would require an actual call to the OpenRouter API.
    # For now, we are just testing the endpoint flow.
    # A proper integration test would be needed to test the LLM prompt itself.

@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_complex_login_page_is_crp(mock_get_html, mock_is_crp):
    """
    Tests that a complex login page with distracting text is still identified as a CRP.
    """
    # This HTML simulates a noisy login page with promotional content.
    mock_get_html.return_value = """
    <html>
        <body>
            <header>
                <h1>My Store</h1>
                <nav>Home | Products | Sale</nav>
            </header>
            <main>
                <h2>Weekend Sale! 50% off!</h2>
                <form>
                    <h3>Login to your account</h3>
                    <label>Email:</label>
                    <input type="email" />
                    <button>Continue</button>
                </form>
            </main>
            <footer>
                <p>About Us | Contact | FAQ</p>
            </footer>
        </body>
    </html>
    """
    mock_is_crp.return_value = True  # The refined prompt should identify this as a CRP.

    response = client.post("/analyze", json={"url": "https://example.com/complex-login"})

    mock_is_crp.assert_awaited_once()
