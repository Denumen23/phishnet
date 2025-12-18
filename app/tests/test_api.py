import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock

client = TestClient(app)

@patch('app.api.endpoints.identify_brand_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.find_logo')
@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_analyze_phishing_url(
    mock_get_html, mock_get_screenshot, mock_find_logo, mock_is_crp, mock_identify_brand
):
    """
    Tests a scenario where a URL is a credential page impersonating a known brand.
    """
    mock_get_html.return_value = "<html><body>Login to your Bank</body></html>"
    mock_get_screenshot.return_value = None
    mock_is_crp.return_value = True
    mock_identify_brand.return_value = "MyBank"
    mock_find_logo.return_value = "MyBank"

    response = client.post("/analyze", json={"url": "http://phishing-example.com"})

    assert response.status_code == 200
    data = response.json()
    assert data['phishing_score'] == 100
    assert data['llm_analysis']['is_credential_page'] is True
    assert data['llm_analysis']['identified_brand'] == "MyBank"
    assert data['matched_brand_logo'] == "MyBank"

@patch('app.api.endpoints.identify_brand_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.find_logo')
@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_analyze_non_credential_page(
    mock_get_html, mock_get_screenshot, mock_find_logo, mock_is_crp, mock_identify_brand
):
    """
    Tests a scenario where a URL is a safe, non-credential page.
    """
    mock_get_html.return_value = "<html><body>Welcome to my blog</body></html>"
    mock_get_screenshot.return_value = None
    mock_is_crp.return_value = False
    mock_find_logo.return_value = None

    response = client.post("/analyze", json={"url": "http://safe-example.com"})

    assert response.status_code == 200
    data = response.json()
    assert data['phishing_score'] == 0
    assert data['llm_analysis']['is_credential_page'] is False
    assert data['llm_analysis']['identified_brand'] is None

    # Ensure the second LLM call is not made for non-CRP pages
    mock_identify_brand.assert_not_called()

@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_analyze_url_fetch_fails(mock_get_html):
    """
    Tests the /analyze endpoint when fetching the HTML fails.
    """
    mock_get_html.return_value = ""

    response = client.post("/analyze", json={"url": "https://bad-url.com"})

    assert response.status_code == 400
    assert "Could not fetch HTML from the URL." in response.json()['detail']
