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


def test_room_history_reconciles_a_bot_announcement() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path.endswith("RoomService/GetRoomEvents")
        return httpx.Response(
            200,
            json={
                "page": {
                    "events": [
                        {
                            "actorId": "bot-1",
                            "messagePosted": {
                                "message": {
                                    "actorId": "bot-1",
                                    "body": "Chatto 0.5.0-beta.1\nhttps://release.example/v0.5.0-beta.1",
                                }
                            },
                        }
                    ],
                    "hasOlder": False,
                }
            },
        )

    client = ChattoClient(
        "https://chatto.example", httpx.Client(transport=httpx.MockTransport(handler))
    )

    assert client.room_has_announcement(
        "room-1", "bot-key", "bot-1", "https://release.example/v0.5.0-beta.1"
    )


def test_room_history_failure_is_not_treated_as_empty() -> None:
    client = ChattoClient(
        "https://chatto.example",
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403))),
    )

    with pytest.raises(ChattoError, match="timeline"):
        client.room_has_announcement("room-1", "bot-key", "bot-1", "release")
