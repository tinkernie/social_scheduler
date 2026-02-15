# social_scheduler

This project provides a backend for creating and scheduling social posts.

## Telegram publishing flow

The post creation endpoint now relays posts through a Telegram bot instead of a proxy layer:

1. User submits a post to `POST /posts/`.
2. The API sends the post payload to Telegram Bot API (`sendMessage`).
3. Telegram bot posts to the configured chat/channel.
4. If Telegram publish succeeds, the post is committed to the database.

## Required environment variables

- `TELEGRAM_BOT_TOKEN`: Bot token from BotFather.
- `TELEGRAM_CHAT_ID`: Target chat or channel id where posts should be published.
