import httpx
import pytest

from chatto_releasebot.github import GitHubReleaseClient, ReleasePending


def test_resolves_exact_prerelease_tag() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/releases/tags/v0.5.0-beta.1")
        return httpx.Response(
            200,
            json={
                "tag_name": "v0.5.0-beta.1",
                "html_url": "https://github.com/chattocorp/chatto/releases/tag/v0.5.0-beta.1",
                "body": "### Features\n\n* improve calls",
                "draft": False,
            },
        )

    client = GitHubReleaseClient(httpx.Client(transport=httpx.MockTransport(handler)))

    release = client.get_release("0.5.0-beta.1")

    assert release.tag == "v0.5.0-beta.1"
    assert release.url.endswith("v0.5.0-beta.1")
    assert "improve calls" in release.body


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404),
        httpx.Response(
            200, json={"tag_name": "authling/v0.5.0-beta.1", "draft": False}
        ),
        httpx.Response(200, json={"tag_name": "v0.5.0-beta.1", "draft": True}),
    ],
)
def test_missing_or_wrong_release_is_pending(response: httpx.Response) -> None:
    client = GitHubReleaseClient(
        httpx.Client(transport=httpx.MockTransport(lambda _: response))
    )

    with pytest.raises(ReleasePending):
        client.get_release("0.5.0-beta.1")
