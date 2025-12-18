import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock

client = TestClient(app)

@patch('app.api.endpoints.brand_normalizer')
@patch('app.api.endpoints.identify_brand_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.find_logo')
@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_analyze_phishing_url_with_normalization(
    mock_get_html, mock_get_screenshot, mock_find_logo, mock_is_crp, mock_identify_brand, mock_normalizer
):
    """
    Tests a phishing scenario with brand normalization.
    """
    mock_get_html.return_value = "<html><body>Login to your MS account</body></html>"
    mock_get_screenshot.return_value = None
    mock_is_crp.return_value = True
    mock_identify_brand.return_value = "MS"
    mock_find_logo.return_value = "Microsoft"

    # Configure the mock normalizer
    def normalize_side_effect(alias):
        if alias.lower() in ["ms", "microsoft"]:
            return "Microsoft"
        return None
    mock_normalizer.normalize_brand.side_effect = normalize_side_effect

    response = client.post("/analyze", json={"url": "http://phishing-ms.com"})

    assert response.status_code == 200
    data = response.json()
    assert data['phishing_score'] == 100
    assert data['llm_analysis']['is_credential_page'] is True
    assert data['llm_analysis']['identified_brand_alias'] == "MS"
    assert data['llm_analysis']['canonical_brand'] == "Microsoft"
    assert data['matched_brand_logo_alias'] == "Microsoft"
    assert data['canonical_brand_logo'] == "Microsoft"

@patch('app.api.endpoints.identify_brand_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.is_credential_page_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.find_logo')
@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_analyze_non_credential_page(
    mock_get_html, mock_get_screenshot, mock_find_logo, mock_is_crp, mock_identify_brand
):
    """
    Tests a safe, non-credential page.
    """
    mock_get_html.return_value = "<html><body>A regular blog post</body></html>"
    mock_get_screenshot.return_value = None
    mock_is_crp.return_value = False
    mock_find_logo.return_value = None

    response = client.post("/analyze", json={"url": "http://safe-blog.com"})

    assert response.status_code == 200
    data = response.json()
    assert data['phishing_score'] == 0
    assert data['llm_analysis']['is_credential_page'] is False
    mock_identify_brand.assert_not_called()

@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_analyze_url_fetch_fails(mock_get_html):
    """
    Tests the endpoint when HTML fetching fails.
    """
    mock_get_html.return_value = ""

    response = client.post("/analyze", json={"url": "https://bad-url.com"})

    assert response.status_code == 400
    assert "Could not fetch HTML" in response.json()['detail']
