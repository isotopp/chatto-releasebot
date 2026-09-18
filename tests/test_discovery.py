import httpx
import pytest

from chatto_releasebot.chatto import ChattoClient, ChattoError


def test_discovery_returns_live_prerelease_version() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert (
            request.url.path
            == "/api/connect/chatto.discovery.v1.ServerDiscoveryService/GetServer"
        )
        assert request.headers["content-type"] == "application/json"
        assert request.read() == b"{}"
        return httpx.Response(200, json={"profile": {"version": "0.5.0-beta.1"}})

    client = ChattoClient(
        "https://chatto.example", httpx.Client(transport=httpx.MockTransport(handler))
    )

    assert client.discover_version() == "0.5.0-beta.1"


@pytest.mark.parametrize("payload", [{}, {"profile": {}}, {"profile": {"version": ""}}])
def test_discovery_rejects_missing_version(payload: dict[str, object]) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    client = ChattoClient("https://chatto.example", httpx.Client(transport=transport))

    with pytest.raises(ChattoError, match="version"):
        client.discover_version()
