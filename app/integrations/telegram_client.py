"""
telegram_client.py — Send build notifications to founder via Telegram.

Free, instant, no setup cost. Use Telegram Bot API directly via httpx.
Works globally. No email infrastructure needed.

Setup instructions for founder:
1. Open Telegram, search @BotFather
2. Send /newbot, follow steps, get your BOT_TOKEN
3. Start a chat with your bot, then open:
   https://api.telegram.org/bot{TOKEN}/getUpdates
4. Find your chat_id in the response
5. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to Vercel env vars
"""

import logging

import httpx

logger = logging.getLogger(__name__)


class TelegramClient:
    """Send messages to a Telegram chat via Bot API."""

    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token: str = "", chat_id: str = "") -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, message: str) -> bool:
        """Send a plain text message. Returns True on success."""
        if not self.is_configured:
            logger.debug("Telegram not configured — skipping notification")
            return False
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    f"{self.BASE_URL}/bot{self.bot_token}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": "HTML",
                    },
                )
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.warning("Telegram notification failed: %s", exc)
            return False

    def notify_build_started(self, project_name: str, run_id: str) -> bool:
        return self.send(
            f"\U0001f3ed <b>Build started</b>\n"
            f"Project: {project_name}\n"
            f"Run ID: {run_id}"
        )

    def notify_build_success(self, project_name: str, deploy_url: str) -> bool:
        return self.send(
            f"\u2705 <b>Build succeeded!</b>\n"
            f"Project: <b>{project_name}</b>\n"
            f"Live at: {deploy_url}\n\n"
            f"\U0001f4e3 Time to launch!"
        )

    def notify_build_failed(self, project_name: str, error: str) -> bool:
        return self.send(
            f"\u274c <b>Build failed</b>\n"
            f"Project: {project_name}\n"
            f"Error: {error[:200]}"
        )

    def notify_idea_approved(self, title: str, score: float) -> bool:
        return self.send(
            f"\U0001f4a1 <b>Idea approved!</b>\n"
            f"<b>{title}</b> scored {score}/10\n"
            f"Ready to build."
        )
