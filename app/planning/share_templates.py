"""
Share templates – generates ready-to-use distribution messages for multiple platforms.

Each platform message is tailored to the platform's tone, length, and audience.
No external API calls are made; all copy is generated deterministically.
"""

from __future__ import annotations

from pydantic import BaseModel


class ShareMessageBundle(BaseModel):
    """Collection of platform-specific distribution messages."""

    twitter: str
    linkedin: str
    whatsapp: str
    email_subject: str
    email_body: str
    sms: str
    reddit_title: str
    product_hunt_tagline: str


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len characters, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def generate_share_messages(
    *,
    title: str,
    url: str,
    description: str,
    target_user: str,
    cta: str,
) -> ShareMessageBundle:
    """Generate platform-optimised distribution messages.

    Args:
        title: Product name or idea title.
        url: Deployment URL (included in all messages).
        description: Short product description (1–2 sentences).
        target_user: Primary audience (e.g. "freelance developers").
        cta: Call-to-action text (e.g. "Try it free").

    Returns:
        ShareMessageBundle with messages for all supported platforms.
    """
    # ------------------------------------------------------------------
    # Twitter / X  (max 280 chars)
    # ------------------------------------------------------------------
    twitter_raw = (
        f"🚀 Introducing {title}\n\n"
        f"{description}\n\n"
        f"Built for {target_user}.\n\n"
        f"{cta} → {url}"
    )
    twitter = _truncate(twitter_raw, 280)

    # ------------------------------------------------------------------
    # LinkedIn  (professional tone, no strict length)
    # ------------------------------------------------------------------
    linkedin = (
        f"Excited to share {title} 🎯\n\n"
        f"I built this for {target_user} who are frustrated with manual, "
        f"time-consuming processes.\n\n"
        f"{description}\n\n"
        f"The result: less time wasted, more focus on what matters.\n\n"
        f"👉 {cta}: {url}\n\n"
        f"Would love your feedback — drop a comment or DM me!"
    )

    # ------------------------------------------------------------------
    # WhatsApp  (casual tone + emoji)
    # ------------------------------------------------------------------
    whatsapp = (
        f"Hey! 👋 Just launched something cool — {title}\n\n"
        f"{description}\n\n"
        f"Perfect if you're a {target_user} 🙌\n\n"
        f"Check it out 👉 {url}\n\n"
        f"{cta} — would love to know what you think! 💬"
    )

    # ------------------------------------------------------------------
    # Email subject  (concise, action-oriented)
    # ------------------------------------------------------------------
    email_subject = f"{title} — {cta}"

    # ------------------------------------------------------------------
    # Email body  (structured, professional)
    # ------------------------------------------------------------------
    email_body = (
        f"Hi there,\n\n"
        f"I wanted to share something I built specifically for {target_user}.\n\n"
        f"{title}: {description}\n\n"
        f"Here's what makes it different:\n"
        f"• Designed from the ground up for {target_user}\n"
        f"• Saves hours of manual work every week\n"
        f"• {cta} — no complicated setup required\n\n"
        f"Try it now: {url}\n\n"
        f"I'd genuinely love your feedback. Hit reply and let me know what you think.\n\n"
        f"Best,\n"
        f"The {title} Team"
    )

    # ------------------------------------------------------------------
    # SMS  (max 160 chars)
    # ------------------------------------------------------------------
    sms_raw = f"{title}: {description} {cta} → {url}"
    sms = _truncate(sms_raw, 160)

    # ------------------------------------------------------------------
    # Reddit title  (curiosity-driven, community-friendly)
    # ------------------------------------------------------------------
    reddit_title = (
        f"I built {title} for {target_user} — {description} [{cta}]"
    )

    # ------------------------------------------------------------------
    # Product Hunt tagline  (concise punchy hook, max ~60 chars)
    # ------------------------------------------------------------------
    tagline_raw = description.rstrip(".").rstrip(",")
    product_hunt_tagline = _truncate(tagline_raw, 60)

    return ShareMessageBundle(
        twitter=twitter,
        linkedin=linkedin,
        whatsapp=whatsapp,
        email_subject=email_subject,
        email_body=email_body,
        sms=sms,
        reddit_title=reddit_title,
        product_hunt_tagline=product_hunt_tagline,
    )
