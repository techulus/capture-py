import pytest
from aiohttp import web
from capture import Capture, CaptureSessionsError


async def start_test_server(handler):
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}"


def test_capture_initialization():
    client = Capture("test_key", "test_secret")
    assert client.key == "test_key"
    assert client.secret == "test_secret"
    assert client.options == {}


def test_capture_with_edge_option():
    client = Capture("test_key", "test_secret", {"useEdge": True})
    assert client.options.get("useEdge") is True


def test_build_image_url():
    client = Capture("test", "test")
    url = client.build_image_url("https://news.ycombinator.com/")
    expected_url = "https://cdn.capture.page/test/f37d5fb3ee4540a05bf4ffeed6dffa28/image?url=https%3A%2F%2Fnews.ycombinator.com%2F"
    assert url == expected_url


def test_build_image_url_with_options():
    client = Capture("test", "secret")
    url = client.build_image_url(
        "https://news.ycombinator.com/", {"full": True, "delay": 2}
    )
    assert "full=true" in url
    assert "delay=2" in url
    assert "url=https%3A%2F%2Fnews.ycombinator.com%2F" in url


def test_build_pdf_url():
    client = Capture("test", "secret")
    url = client.build_pdf_url("https://example.com")
    assert "/pdf?" in url
    assert "url=https%3A%2F%2Fexample.com" in url


def test_build_content_url():
    client = Capture("test", "secret")
    url = client.build_content_url("https://example.com")
    assert "/content?" in url
    assert "url=https%3A%2F%2Fexample.com" in url


def test_build_metadata_url():
    client = Capture("test", "secret")
    url = client.build_metadata_url("https://example.com")
    assert "/metadata?" in url
    assert "url=https%3A%2F%2Fexample.com" in url


def test_build_animated_url():
    client = Capture("test", "secret")
    url = client.build_animated_url("https://example.com")
    assert "/animated?" in url
    assert "url=https%3A%2F%2Fexample.com" in url


def test_edge_url_when_use_edge_enabled():
    client = Capture("test", "secret", {"useEdge": True})
    url = client.build_image_url("https://example.com")
    assert url.startswith("https://edge.capture.page")


def test_cdn_url_when_use_edge_disabled():
    client = Capture("test", "secret")
    url = client.build_image_url("https://example.com")
    assert url.startswith("https://cdn.capture.page")


def test_missing_key_raises_error():
    client = Capture("", "secret")
    with pytest.raises(ValueError, match="Key and Secret is required"):
        client.build_image_url("https://example.com")


def test_missing_secret_raises_error():
    client = Capture("test", "")
    with pytest.raises(ValueError, match="Key and Secret is required"):
        client.build_image_url("https://example.com")


def test_invalid_url_type_raises_error():
    client = Capture("test", "secret")
    with pytest.raises(TypeError, match="url should be of type string"):
        client.build_image_url(123)


def test_none_url_raises_error():
    client = Capture("test", "secret")
    with pytest.raises(ValueError, match="url is required"):
        client.build_image_url(None)


def test_filter_none_values():
    client = Capture("test", "test")
    url = client.build_image_url(
        "https://example.com", {"none_value": None, "valid": "value"}
    )
    assert "none_value=" not in url
    assert "valid=value" in url


def test_token_generation():
    client = Capture("test", "test")
    token = client._generate_token("test", "url=https%3A%2F%2Fnews.ycombinator.com%2F")
    assert token == "f37d5fb3ee4540a05bf4ffeed6dffa28"


def test_boolean_option_encoding():
    client = Capture("test", "secret")
    url = client.build_image_url("https://example.com", {"full": True, "lazy": False})
    assert "full=true" in url
    assert "lazy=false" in url


def test_numeric_option_encoding():
    client = Capture("test", "secret")
    url = client.build_image_url("https://example.com", {"delay": 5, "quality": 80})
    assert "delay=5" in url
    assert "quality=80" in url


def test_keep_zero_and_false_values():
    client = Capture("test", "test")
    url = client.build_image_url(
        "https://example.com",
        {"delay": 0, "top": 0, "left": 0, "full": False, "darkMode": False},
    )
    assert "delay=0" in url
    assert "top=0" in url
    assert "left=0" in url
    assert "full=false" in url
    assert "darkMode=false" in url


@pytest.mark.asyncio
async def test_fetch_image():
    client = Capture("test", "secret")
    url = client.build_image_url("https://example.com")
    assert url is not None


@pytest.mark.asyncio
async def test_fetch_pdf():
    client = Capture("test", "secret")
    url = client.build_pdf_url("https://example.com")
    assert url is not None


@pytest.mark.asyncio
async def test_fetch_content():
    client = Capture("test", "secret")
    url = client.build_content_url("https://example.com")
    assert url is not None


@pytest.mark.asyncio
async def test_fetch_metadata():
    client = Capture("test", "secret")
    url = client.build_metadata_url("https://example.com")
    assert url is not None


@pytest.mark.asyncio
async def test_fetch_animated():
    client = Capture("test", "secret")
    url = client.build_animated_url("https://example.com")
    assert url is not None


@pytest.mark.asyncio
async def test_create_session_uses_bearer_auth_and_json_body(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(
            {
                "method": request.method,
                "path": request.path,
                "authorization": request.headers.get("Authorization"),
                "body": await request.json(),
            }
        )
        return web.json_response(
            {"success": True, "session": {"id": "sess_123", "status": "active"}},
            status=201,
        )

    runner, base_url = await start_test_server(handler)
    try:
        monkeypatch.setattr(Capture, "EDGE_URL", base_url)
        client = Capture("user_123", "secret")
        response = await client.create_session({"maxTtlSeconds": 300, "proxy": True})

        assert response["session"]["id"] == "sess_123"
        assert requests == [
            {
                "method": "POST",
                "path": "/v1/sessions",
                "authorization": "Bearer dXNlcl8xMjM6c2VjcmV0",
                "body": {"maxTtlSeconds": 300, "proxy": True},
            }
        ]
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_get_close_and_execute_action_requests(monkeypatch):
    requests = []

    async def handler(request):
        body = await request.json() if request.can_read_body else None
        requests.append(
            (request.method, request.path, request.headers.get("Authorization"), body)
        )
        return web.json_response({"success": True, "session": {"id": "sess_123"}})

    runner, base_url = await start_test_server(handler)
    try:
        monkeypatch.setattr(Capture, "EDGE_URL", base_url)
        client = Capture("user_123", "secret")

        await client.get_session("sess_123")
        await client.close_session("sess_123")
        await client.execute_action("sess_123", "goto", {"url": "https://example.com"})

        assert requests == [
            ("GET", "/v1/sessions/sess_123", "Bearer dXNlcl8xMjM6c2VjcmV0", None),
            ("DELETE", "/v1/sessions/sess_123", "Bearer dXNlcl8xMjM6c2VjcmV0", None),
            (
                "POST",
                "/v1/sessions/sess_123/actions",
                "Bearer dXNlcl8xMjM6c2VjcmV0",
                {"type": "goto", "payload": {"url": "https://example.com"}},
            ),
        ]
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_sessions_error_contains_status_and_body(monkeypatch):
    async def handler(request):
        return web.json_response(
            {"success": False, "error": "Session not found"},
            status=404,
        )

    runner, base_url = await start_test_server(handler)
    try:
        monkeypatch.setattr(Capture, "EDGE_URL", base_url)
        client = Capture("user_123", "secret")

        with pytest.raises(CaptureSessionsError) as exc:
            await client.get_session("missing")

        assert exc.value.status == 404
        assert exc.value.body == {"success": False, "error": "Session not found"}
        assert str(exc.value) == "Session not found"
    finally:
        await runner.cleanup()
