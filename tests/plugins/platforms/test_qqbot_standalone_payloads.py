"""Standalone QQ Bot text payload contracts, independent of Telegram extras."""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch


class _FakeQqbotResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


class TestSendQqbotStandalonePayloads:
    def _run(self, message="**bold**\n- item", extra=None, c2c_status=200):
        from plugins.platforms.qqbot.send import send_qqbot as _send_qqbot

        pconfig = SimpleNamespace(
            token="secret",
            extra={"app_id": "app-1", **(extra or {})},
        )
        calls = {}

        class _FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, json=None, headers=None):
                calls.setdefault("posts", []).append(
                    {"url": url, "json": json, "headers": headers}
                )
                if url.endswith("/app/getAppAccessToken"):
                    return _FakeQqbotResponse(200, {"access_token": "tok-123"})
                if "/channels/" in url:
                    return _FakeQqbotResponse(404)
                if "/v2/users/" in url:
                    return _FakeQqbotResponse(c2c_status, {"id": "c2c-msg-1"})
                return _FakeQqbotResponse(200, {"id": "grp-msg-1"})

        with patch("httpx.AsyncClient", _FakeAsyncClient):
            result = asyncio.run(_send_qqbot(pconfig, "chat-1", message))
        return result, calls["posts"]

    def test_channel_request_uses_plain_content_payload(self):
        result, posts = self._run()
        assert result["success"] is True
        channel_post = next(
            p for p in posts if "/channels/" in p["url"]
        )
        # Guild channel contract: plain content body only, no markdown.
        assert channel_post["json"] == {"content": "**bold**\n- item"}

    def test_markdown_fallback_default(self):
        _, posts = self._run()
        c2c_post = next(p for p in posts if "/v2/users/" in p["url"])
        assert c2c_post["json"] == {
            "markdown": {"content": "**bold**\n- item"}, "msg_type": 2,
        }

    def test_plain_text_fallback_when_markdown_disabled(self):
        _, posts = self._run(extra={"markdown_support": False})
        c2c_post = next(p for p in posts if "/v2/users/" in p["url"])
        assert c2c_post["json"] == {
            "content": "**bold**\n- item", "msg_type": 0,
        }

    def test_group_fallback_uses_same_payload_as_c2c(self):
        # Group endpoint is reached only when C2C also fails.
        result, posts = self._run(c2c_status=404)
        assert result["success"] is True
        group_post = next(p for p in posts if "/v2/groups/" in p["url"])
        assert group_post["json"] == {
            "markdown": {"content": "**bold**\n- item"}, "msg_type": 2,
        }
