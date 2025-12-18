import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock
import json

client = TestClient(app)

@patch('app.api.endpoints.analyze_text_with_llm', new_callable=AsyncMock)
@patch('app.api.endpoints.find_logo')
@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_analyze_url_success(
    mock_get_html, mock_get_screenshot, mock_find_logo, mock_analyze_llm
):
    """
    Tests the /analyze endpoint with a successful scenario.
    """
    # Configure mocks
    mock_get_html.return_value = "<html><body>Mocked HTML Content</body></html>"
    mock_get_screenshot.return_value = None
    mock_find_logo.return_value = "google"
    mock_analyze_llm.return_value = {
        "result": "safe",
        "reasoning": "The content seems legitimate."
    }

    # Make the request
    response = client.post("/analyze", json={"url": "https://example.com"})

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data['url'] == "https://example.com"
    assert data['phishing_score'] == 10
    assert data['matched_brand'] == "google"
    assert data['llm_analysis']['result'] == "safe"

@patch('app.api.endpoints.get_screenshot', new_callable=AsyncMock)
@patch('app.api.endpoints.get_html', new_callable=AsyncMock)
def test_analyze_url_html_fetch_fails(mock_get_html, mock_get_screenshot):
    """
    Tests the /analyze endpoint when fetching the HTML fails.
    """
    # Configure mock to simulate failure
    mock_get_html.return_value = ""
    mock_get_screenshot.return_value = None

    # Make the request
    response = client.post("/analyze", json={"url": "https://bad-url.com"})

    # Assertions
    assert response.status_code == 400
    assert "Could not fetch HTML from the URL." in response.json()['detail']
