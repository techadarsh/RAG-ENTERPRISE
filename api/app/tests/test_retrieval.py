
# Test for the /chat endpoint in the Enterprise RAG API.
#
# This test is designed to validate the basic response structure of the /chat endpoint.
# It does NOT require Milvus, embeddings, or Ollama to be running; it only checks that the API
# returns a valid JSON response with the expected keys and types, even if dependencies are down.
#
# This ensures that the FastAPI route, request/response models, and error handling are robust.

from fastapi.testclient import TestClient
from app.main import app

# Create a test client for the FastAPI app
client = TestClient(app)

def test_chat_shape():
    """
    Test the /chat endpoint for correct response shape.

    - Sends a POST request with a sample query and top_k value.
    - Asserts that the response is HTTP 200 OK.
    - Asserts that the response JSON contains 'answer' and 'contexts' keys.
    - Asserts that 'contexts' is always a list (may be empty if no docs ingested or deps are down).

    This test does not require any external services to be running and will pass as long as the
    endpoint is mounted and the response model is correct.
    """
    r = client.post("/chat", json={"query": "What is this project?", "top_k": 3})
    assert r.status_code == 200, "Expected HTTP 200 OK from /chat endpoint"
    data = r.json()
    assert "answer" in data, "Response should contain 'answer' key"
    assert "contexts" in data, "Response should contain 'contexts' key"
    assert isinstance(data["contexts"], list), "'contexts' should be a list"
