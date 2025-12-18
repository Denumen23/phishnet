import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock

client = TestClient(app)

@patch('app.api.endpoints.domain_checker')
@patch('app.api.endpoints.brand_normalizer')
@patch('app.api.endpoints.identify_brand_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.find_logo')
@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_legitimate_login_page(
    mock_get_html, mock_get_screenshot, mock_find_logo, mock_is_crp, mock_identify_brand, mock_normalizer, mock_domain_checker
):
    """
    Tests a legitimate login page, which should result in a low phishing score.
    """
    mock_get_html.return_value = "<html><body>Sign in to Microsoft</body></html>"
    mock_get_screenshot.return_value = None
    mock_is_crp.return_value = True
    mock_identify_brand.return_value = "Microsoft"
    mock_find_logo.return_value = "Microsoft"
    mock_normalizer.normalize_brand.return_value = "Microsoft"
    mock_domain_checker.is_legitimate_domain.return_value = True

    response = client.post("/analyze", json={"url": "https://login.microsoft.com"})

    assert response.status_code == 200
    data = response.json()
    assert data['phishing_score'] == 5
    assert data['domain_analysis']['is_legitimate'] is True

@patch('app.api.endpoints.domain_checker')
@patch('app.api.endpoints.brand_normalizer')
@patch('app.api.endpoints.identify_brand_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.find_logo')
@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_phishing_page_on_mismatched_domain(
    mock_get_html, mock_get_screenshot, mock_find_logo, mock_is_crp, mock_identify_brand, mock_normalizer, mock_domain_checker
):
    """
    Tests a phishing page on a mismatched domain, which should result in a high phishing score.
    """
    mock_get_html.return_value = "<html><body>Sign in to Microsoft</body></html>"
    mock_get_screenshot.return_value = None
    mock_is_crp.return_value = True
    mock_identify_brand.return_value = "Microsoft"
    mock_find_logo.return_value = "Microsoft"
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
