import httpx
import pytest

from chatto_releasebot.chatto import ChattoClient, ChattoError
from chatto_releasebot.config import Config, ConfigError


def test_create_message_posts_one_authenticated_root_message() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.method == "POST"
        assert request.url.path.endswith("MessageService/CreateMessage")
        assert request.headers["Authorization"] == "Bearer secret-key"
        assert request.read().decode() == '{"roomId":"room-1","body":"hello"}'
        return httpx.Response(200, json={"message": {"id": "event-1"}})

    client = ChattoClient(
        "https://chatto.example", httpx.Client(transport=httpx.MockTransport(handler))
    )

    client.create_message("room-1", "hello", "secret-key")

    assert len(seen) == 1


def test_denied_message_is_not_success_and_does_not_leak_key() -> None:
    client = ChattoClient(
        "https://chatto.example",
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403))),
    )

    with pytest.raises(ChattoError) as error:
        client.create_message("room-1", "hello", "secret-key")

    assert "secret-key" not in str(error.value)


def test_config_rejects_missing_required_values() -> None:
    with pytest.raises(ConfigError, match="ANNOUNCEMENTS_API_KEY"):
        Config.from_env(
            {
                "ANNOUNCEMENTS_SERVER_BASE_URL": "https://chatto.example",
                "ANNOUNCEMENTS_ROOM_ID": "room-1",
            }
        )
