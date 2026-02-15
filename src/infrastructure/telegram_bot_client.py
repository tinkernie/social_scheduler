import os
from typing import Optional

import httpx


class TelegramBotError(Exception):
    pass


class TelegramBotClient:
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: int = 30,
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.timeout = timeout

        if not self.bot_token:
            raise TelegramBotError("TELEGRAM_BOT_TOKEN is not configured")

        if not self.chat_id:
            raise TelegramBotError("TELEGRAM_CHAT_ID is not configured")

        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def publish_post(self, title: Optional[str], content: Optional[str], media_path: Optional[str]) -> dict:
        message_parts = []
        if title:
            message_parts.append(f"<b>{title}</b>")
        if content:
            message_parts.append(content)
        if media_path:
            message_parts.append(f"Media: {media_path}")

        text = "\n\n".join(message_parts).strip()
        if not text:
            raise TelegramBotError("Post content is empty; nothing to publish to Telegram")

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/sendMessage", json=payload)

        if response.status_code >= 400:
            raise TelegramBotError(f"Telegram API error ({response.status_code}): {response.text}")

        body = response.json()
        if not body.get("ok"):
            raise TelegramBotError(f"Telegram API rejected message: {body}")

        return body
