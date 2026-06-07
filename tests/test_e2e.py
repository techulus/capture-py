import os

import pytest

from capture import Capture

CAPTURE_API_KEY = os.environ.get("CAPTURE_API_KEY")
CAPTURE_API_SECRET = os.environ.get("CAPTURE_API_SECRET")
CAPTURE_LIVE_SESSIONS = os.environ.get("CAPTURE_LIVE_SESSIONS") == "1"
TEST_URL = "https://techulus.xyz"

skip_if_no_credentials = pytest.mark.skipif(
    not CAPTURE_API_KEY or not CAPTURE_API_SECRET,
    reason="E2E tests require CAPTURE_API_KEY and CAPTURE_API_SECRET environment variables"
)

skip_if_no_session_credentials = pytest.mark.skipif(
    not CAPTURE_LIVE_SESSIONS or not CAPTURE_API_KEY or not CAPTURE_API_SECRET,
    reason=(
        "Live sessions test requires CAPTURE_LIVE_SESSIONS=1, CAPTURE_API_KEY, "
        "and CAPTURE_API_SECRET"
    ),
)

@pytest.fixture
def client():
    return Capture(CAPTURE_API_KEY, CAPTURE_API_SECRET)

@pytest.fixture
def edge_client():
    return Capture(CAPTURE_API_KEY, CAPTURE_API_SECRET, {"useEdge": True})

@skip_if_no_credentials
@pytest.mark.asyncio
async def test_fetch_image_successfully(client):
    image_data = await client.fetch_image(TEST_URL)
    assert isinstance(image_data, bytes)
    assert len(image_data) > 0

@skip_if_no_credentials
@pytest.mark.asyncio
async def test_fetch_pdf_successfully(client):
    pdf_data = await client.fetch_pdf(TEST_URL)
    assert isinstance(pdf_data, bytes)
    assert len(pdf_data) > 0

@skip_if_no_credentials
@pytest.mark.asyncio
async def test_fetch_content_successfully(client):
    content = await client.fetch_content(TEST_URL)
    assert content["success"] is True
    assert "html" in content
    assert "textContent" in content
    assert len(content["html"]) > 0

@skip_if_no_credentials
@pytest.mark.asyncio
async def test_fetch_metadata_successfully(client):
    metadata = await client.fetch_metadata(TEST_URL)
    assert metadata["success"] is True
    assert "metadata" in metadata
    assert len(metadata["metadata"]) > 0

@skip_if_no_credentials
@pytest.mark.asyncio
async def test_fetch_animated_successfully(client):
    animated_data = await client.fetch_animated(TEST_URL)
    assert isinstance(animated_data, bytes)
    assert len(animated_data) > 0

@skip_if_no_credentials
@pytest.mark.asyncio
async def test_fetch_image_with_options(client):
    image_data = await client.fetch_image(TEST_URL, {"full": True, "delay": 2})
    assert isinstance(image_data, bytes)
    assert len(image_data) > 0

@skip_if_no_credentials
@pytest.mark.asyncio
async def test_edge_url_fetches_successfully(edge_client):
    image_data = await edge_client.fetch_image(TEST_URL)
    assert isinstance(image_data, bytes)
    assert len(image_data) > 0

@skip_if_no_credentials
@pytest.mark.asyncio
async def test_all_fetch_methods_together(client):
    image_data = await client.fetch_image(TEST_URL)
    assert len(image_data) > 0

    pdf_data = await client.fetch_pdf(TEST_URL)
    assert len(pdf_data) > 0

    content = await client.fetch_content(TEST_URL)
    assert content["success"] is True
    assert len(content["html"]) > 0

    metadata = await client.fetch_metadata(TEST_URL)
    assert metadata["success"] is True
    assert metadata["metadata"]


@skip_if_no_session_credentials
@pytest.mark.asyncio
async def test_live_session_screenshot_example_dot_com():
    client = Capture(CAPTURE_API_KEY, CAPTURE_API_SECRET)
    session_id = None

    try:
        created = await client.create_session({"maxTtlSeconds": 300})
        session_id = created["session"]["id"]

        await client.execute_action(
            session_id,
            "goto",
            {"url": "https://example.com"},
        )
        screenshot = await client.execute_action(
            session_id,
            "screenshot",
            {"fullPage": True},
        )

        result = screenshot.get("result", screenshot)
        if isinstance(result, dict) and isinstance(result.get("screenshot"), dict):
            result = result["screenshot"]

        content_type = result.get("contentType") or result.get("mimeType")
        body_base64 = result.get("bodyBase64") or result.get("base64")

        assert content_type == "image/png"
        assert isinstance(body_base64, str)
        assert len(body_base64) > 0
    finally:
        if session_id:
            await client.close_session(session_id)
