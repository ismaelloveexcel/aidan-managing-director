"""
marketing_engine.py — Region-aware marketing campaign generator for AI-DAN.

Given a product and target region, generates platform-specific marketing
content using the best available AI model. Uses Grok (xAI) preferentially
for regional content because it has real-time web access and knows what
is trending RIGHT NOW in each region.

Platform priority by region:
  MENA (UAE, Saudi, Egypt, etc.) → Instagram, TikTok, Snapchat, WhatsApp, YouTube
  Sub-Saharan Africa              → WhatsApp, Facebook, TikTok, YouTube
  South Asia (India/Pak/BD)       → WhatsApp, Instagram, YouTube, Facebook
  Southeast Asia                  → Facebook, TikTok, Instagram, LINE (TH/JP)
  Latin America                   → Instagram, TikTok, WhatsApp, Facebook
  East Asia                       → WeChat/Weibo (note: separate ecosystem)
  Western Europe                  → Instagram, TikTok, Facebook, LinkedIn, X
  North America                   → TikTok, Instagram, Reddit, X, LinkedIn
  Global/Unknown                  → X, LinkedIn, Instagram, TikTok, Reddit, Email
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.integrations.ai_provider import AIProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Region → Platform map
# ---------------------------------------------------------------------------

REGION_PLATFORMS: dict[str, dict[str, Any]] = {
    "mena": {
        "label": "MENA (Middle East & North Africa)",
        "emoji": "🇦🇪",
        "primary": ["instagram", "tiktok", "snapchat", "whatsapp", "youtube"],
        "notes": "Arabic content performs better. Right-to-left consideration. Ramadan/Eid seasonal hooks are high-value. Aspiration and family values resonate strongly.",
    },
    "africa": {
        "label": "Sub-Saharan Africa",
        "emoji": "🌍",
        "primary": ["whatsapp", "facebook", "tiktok", "youtube"],
        "notes": "WhatsApp is the primary sharing mechanism — viral forwards are huge. Facebook groups are key for community trust. Mobile-first, often limited data — short videos win.",
    },
    "south_asia": {
        "label": "South Asia (India, Pakistan, Bangladesh)",
        "emoji": "🇮🇳",
        "primary": ["whatsapp", "instagram", "youtube", "facebook"],
        "notes": "WhatsApp groups are the primary viral channel. Bollywood/cricket cultural references land well. Price sensitivity is high — free tier or low-cost entry matters.",
    },
    "southeast_asia": {
        "label": "Southeast Asia",
        "emoji": "🌏",
        "primary": ["facebook", "tiktok", "instagram"],
        "notes": "Facebook still dominant in PH, MY, ID. TikTok exploding in TH, VN. Short-form video is king. Fun, playful tone outperforms professional.",
    },
    "latam": {
        "label": "Latin America",
        "emoji": "🌎",
        "primary": ["instagram", "tiktok", "whatsapp", "facebook"],
        "notes": "Instagram Stories and Reels dominate. WhatsApp for direct sharing. Emotional storytelling outperforms feature lists. Spanish/Portuguese content beats English.",
    },
    "europe": {
        "label": "Western Europe",
        "emoji": "🇪🇺",
        "primary": ["instagram", "tiktok", "facebook", "linkedin", "twitter"],
        "notes": "Privacy-conscious audience. GDPR awareness important in messaging. LinkedIn strong for B2B. TikTok growing fast in UK, DE, FR.",
    },
    "north_america": {
        "label": "North America (US & Canada)",
        "emoji": "🇺🇸",
        "primary": ["tiktok", "instagram", "reddit", "twitter", "linkedin"],
        "notes": "Reddit for community validation (Show HN, r/SaaS, r/entrepreneur). X/Twitter for founder community. TikTok for consumer products. LinkedIn for B2B.",
    },
    "global": {
        "label": "Global / Multiple Regions",
        "emoji": "🌍",
        "primary": ["twitter", "linkedin", "instagram", "tiktok", "reddit", "whatsapp"],
        "notes": "English-first. Adapt tone to broad audience. Focus on universal pain points.",
    },
}

# ---------------------------------------------------------------------------
# Platform metadata (emojis + labels for UI)
# ---------------------------------------------------------------------------

PLATFORM_META: dict[str, dict[str, str]] = {
    "instagram": {"emoji": "📸", "label": "Instagram"},
    "tiktok": {"emoji": "🎵", "label": "TikTok"},
    "snapchat": {"emoji": "👻", "label": "Snapchat"},
    "whatsapp": {"emoji": "💬", "label": "WhatsApp"},
    "youtube": {"emoji": "▶️", "label": "YouTube Shorts"},
    "facebook": {"emoji": "👥", "label": "Facebook"},
    "twitter": {"emoji": "𝕏", "label": "X / Twitter"},
    "linkedin": {"emoji": "💼", "label": "LinkedIn"},
    "reddit": {"emoji": "🔴", "label": "Reddit"},
    "email": {"emoji": "📧", "label": "Cold Email"},
    "product_hunt": {"emoji": "🐱", "label": "Product Hunt"},
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_MARKETING_SYSTEM = """\
You are a world-class regional marketing strategist for a solo founder.
You know exactly what content works on each platform in each region.
You generate platform-native content that feels organic, not branded.
Your output is always a single valid JSON object with platform keys as requested.
Be specific, creative, and culturally aware. No generic filler copy."""


def _build_platform_instructions() -> str:
    """Return the JSON field spec for each platform."""
    return """Return a single JSON object where each key is a platform name and the value is an object.

Platform-specific field requirements:

"instagram": {
  "caption": "150-word max caption, conversational and visual",
  "hashtags": ["5-10 relevant hashtags"],
  "reels_hook": "First 3 seconds as text — must stop the scroll",
  "story_cta": "Story CTA idea (e.g. Swipe up to try free)"
}

"tiktok": {
  "hook": "First 2 seconds — must stop the scroll immediately",
  "body": "10-15 second script body",
  "cta": "Last 3 seconds CTA",
  "audio_suggestion": "Describe audio category (e.g. upbeat pop, lo-fi chill)",
  "text_overlays": ["List of 2-3 text overlays to show on screen"]
}

"whatsapp": {
  "message": "3-5 sentence viral forward message, emoji-rich, sounds like from a friend not a brand, ends with link + reason to forward"
}

"facebook": {
  "post": "200-300 word community/group style post, conversational, question hook to drive comments"
}

"snapchat": {
  "story_concept": "10-second story concept: what's on screen",
  "text_overlay": "Text to show on story",
  "sticker_idea": "Fun sticker or filter idea"
}

"twitter": {
  "thread": ["Tweet 1 (hook)", "Tweet 2 (context)", "Tweet 3 (proof/insight)", "Tweet 4 (CTA)"],
  "standalone": "Single standalone tweet under 280 chars"
}

"linkedin": {
  "post": "300-400 word founder story format, professional but personal, lessons learned angle",
  "hashtags": ["3-5 hashtags"]
}

"reddit": {
  "subreddit": "Best subreddit to post in (e.g. r/SaaS)",
  "title": "Post title — no self-promotion tone",
  "body": "Post body — provide value first, mention product naturally"
}

"youtube": {
  "shorts_script": "60-second YouTube Shorts script",
  "title": "SEO-optimized video title",
  "description": "Video description with keywords",
  "tags": ["5-8 relevant tags"]
}

"email": {
  "subject_a": "Subject line option A",
  "subject_b": "Subject line option B (A/B test)",
  "body": "150-word cold outreach body",
  "ps": "PS line",
  "personalization_placeholder": "What to personalize (e.g. [their recent post about X])"
}

"product_hunt": {
  "tagline": "Tagline — max 60 chars",
  "description": "Description — max 260 chars",
  "first_comment": "First comment template to post after launch",
  "gallery_suggestions": ["2-3 gallery image description suggestions"]
}"""


def _stub_content(
    platform: str, title: str, description: str, url: str, cta: str
) -> dict:
    """Return template-based stub content for a platform when AI is unavailable."""
    stubs: dict[str, dict] = {
        "instagram": {
            "caption": (
                f"Introducing {title} ✨\n\n{description}\n\n"
                f"Perfect for anyone ready to level up.\n\n{cta} → link in bio 🔗"
            ),
            "hashtags": ["#launch", "#startup", "#buildinpublic", "#founders", "#tech"],
            "reels_hook": f"POV: You just discovered {title}...",
            "story_cta": f"Swipe up to {cta.lower()}",
        },
        "tiktok": {
            "hook": f"Wait — you need to see {title}...",
            "body": f"{description} This changes everything for your audience.",
            "cta": f"Link in bio to {cta.lower()}!",
            "audio_suggestion": "upbeat pop / trending sound",
            "text_overlays": [f"Introducing {title}", description[:50], cta],
        },
        "whatsapp": {
            "message": (
                f"Hey! 👋 Just found something amazing — {title}\n\n{description}\n\n"
                f"{cta} 👉 {url}\n\nForward this to anyone who needs it! 🙌"
            ),
        },
        "facebook": {
            "post": (
                f"I've been working on something exciting and wanted to share it "
                f"with this community first.\n\n{title} — {description}\n\n"
                f"Who here has struggled with this? Drop a comment below 👇\n\n"
                f"Check it out: {url}\n\n{cta} and let me know what you think!"
            ),
        },
        "snapchat": {
            "story_concept": f"Screen recording of {title} in action with excited reaction",
            "text_overlay": "This is going to change everything 🔥",
            "sticker_idea": "Mind blown emoji / fire sticker",
        },
        "twitter": {
            "thread": [
                f"🚀 Introducing {title} — {description}",
                "Built this for [target user] who are tired of [problem]. Here's what makes it different:",
                "Early users are saying [result]. The feedback has been incredible.",
                f"{cta}: {url}",
            ],
            "standalone": f"Just launched {title} 🚀 {description} {cta} → {url}",
        },
        "linkedin": {
            "post": (
                f"I'm excited to share something I've been building.\n\n"
                f"{title} — {description}\n\n"
                f"The problem I kept seeing: [specific pain point for target users].\n\n"
                f"So I built {title}. Here's what I learned:\n\n"
                "1. [Key insight]\n2. [Key insight]\n3. [Key insight]\n\n"
                f"{cta}: {url}\n\nWould love your feedback in the comments 👇"
            ),
            "hashtags": ["#startup", "#buildinpublic", "#founders"],
        },
        "reddit": {
            "subreddit": "r/SaaS",
            "title": f"I built {title} for [target users] — would love feedback",
            "body": (
                f"Hey r/SaaS,\n\nI've been working on a tool called {title}.\n\n"
                f"{description}\n\n"
                "I'd love honest feedback from this community. "
                f"What are you currently using for this?\n\nLink: {url}"
            ),
        },
        "youtube": {
            "shorts_script": (
                f"[0s] Hook: {title} is going to blow your mind.\n"
                "[5s] Here's the problem it solves: [explain problem]\n"
                "[15s] Here's how it works: [demo]\n"
                "[45s] The result? [outcome]\n"
                f"[55s] {cta}: link in description!"
            ),
            "title": f"{title} — [Key Benefit] in [Simple Way]",
            "description": f"{description}\n\n{cta}: {url}\n\nTags: {title}, startup, tools",
            "tags": [title.lower(), "startup", "tools", "productivity", "buildinpublic"],
        },
        "email": {
            "subject_a": "Quick question about [their pain point]",
            "subject_b": f"{title} — built for [target user]",
            "body": (
                f"Hi [Name],\n\n[Personalized opener].\n\n"
                f"I built {title} because {description.lower()}\n\n"
                f"I think it could help [their specific situation].\n\n"
                f"{cta}: {url}\n\nWorth 2 minutes of your time?"
            ),
            "ps": f"PS — {cta} takes under 60 seconds.",
            "personalization_placeholder": "[their recent post / company / specific challenge]",
        },
        "product_hunt": {
            "tagline": (
                description[:57] + "..." if len(description) > 60 else description
            ),
            "description": f"{title} helps {description[:200]}",
            "first_comment": (
                f"Hey hunters! 👋 I'm the maker of {title}. {description}\n\n"
                "Would love your feedback — what features matter most to you?"
            ),
            "gallery_suggestions": [
                "Hero screenshot showing main dashboard/interface",
                "Before/after comparison showing the problem being solved",
                "Short GIF showing the key workflow in action",
            ],
        },
    }
    return stubs.get(platform, {"content": f"[{platform} content for {title}]"})


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class MarketingEngine:
    """Region-aware marketing campaign generator."""

    def __init__(self, ai_provider: AIProvider) -> None:
        self.ai = ai_provider

    def generate_campaign(
        self,
        *,
        title: str,
        description: str,
        target_user: str,
        url: str,
        cta: str,
        region: str = "global",
        platforms: list[str] | None = None,
    ) -> dict:
        """Generate a complete regional marketing campaign.

        Returns dict with:
        - region: str
        - region_label: str
        - regional_notes: str (key insight for this region)
        - platforms: dict[platform_name -> content_dict]
        - ai_model_used: str
        - trending_hooks: list[str]  (Grok-powered if available, else generic)
        """
        region = region.lower().strip()
        region_cfg = REGION_PLATFORMS.get(region, REGION_PLATFORMS["global"])
        target_platforms = list(platforms) if platforms else list(region_cfg["primary"])

        # Always include email and product_hunt as extras
        for extra in ("email", "product_hunt"):
            if extra not in target_platforms:
                target_platforms.append(extra)

        regional_notes = region_cfg["notes"]

        # -- Try AI generation first -----------------------------------------
        ai_result, model_used = self._generate_with_ai(
            title=title,
            description=description,
            target_user=target_user,
            url=url,
            cta=cta,
            region=region,
            region_label=region_cfg["label"],
            regional_notes=regional_notes,
            target_platforms=target_platforms,
        )

        # -- Get trending hooks (Grok preferred) -----------------------------
        trending_hooks = self._get_trending_hooks(
            title=title,
            region=region,
            region_label=region_cfg["label"],
            target_user=target_user,
        )

        # -- Build platform content dict -------------------------------------
        platform_content: dict[str, dict] = {}
        for p in target_platforms:
            if ai_result and p in ai_result:
                platform_content[p] = ai_result[p]
            else:
                platform_content[p] = _stub_content(p, title, description, url, cta)
            meta = PLATFORM_META.get(p, {"emoji": "📢", "label": p.title()})
            platform_content[p]["_meta"] = meta

        return {
            "region": region,
            "region_label": region_cfg["label"],
            "regional_notes": regional_notes,
            "platforms": platform_content,
            "ai_model_used": model_used,
            "trending_hooks": trending_hooks,
        }

    def _generate_with_ai(
        self,
        *,
        title: str,
        description: str,
        target_user: str,
        url: str,
        cta: str,
        region: str,
        region_label: str,
        regional_notes: str,
        target_platforms: list[str],
    ) -> tuple[dict | None, str]:
        """Make a single AI call to generate all platform content.

        Returns (content_dict_or_None, model_name_used).
        """
        from app.core.config import get_settings

        settings = get_settings()
        platforms_list = ", ".join(target_platforms)

        prompt = (
            f"Generate regional marketing content for this product:\n\n"
            f"PRODUCT: {title}\n"
            f"DESCRIPTION: {description}\n"
            f"TARGET USER: {target_user}\n"
            f"URL: {url}\n"
            f"CTA: {cta}\n"
            f"TARGET REGION: {region_label}\n"
            f"REGIONAL INSIGHT: {regional_notes}\n\n"
            f"Generate content for these platforms ONLY: {platforms_list}\n\n"
            f"{_build_platform_instructions()}\n\n"
            f"Important:\n"
            f"- Make ALL content specific to the {region_label} region and audience\n"
            f"- Use cultural references, tone, and language style appropriate for this region\n"
            f"- The content must feel native to each platform, not copy-pasted between them\n"
            f"- Only include the platforms listed above as keys in your JSON response\n"
            f"Return ONLY valid JSON with no markdown, no explanation, just the JSON object."
        )

        messages = [{"role": "user", "content": prompt}]

        # 1. Claude
        if settings.anthropic_api_key:
            result = self._call_anthropic_json(
                messages, settings.anthropic_api_key, settings.anthropic_model
            )
            if result:
                return result, f"claude ({settings.anthropic_model})"

        # 2. OpenAI
        if self.ai.openai.is_configured:
            try:
                result = self.ai.openai.chat_json(
                    prompt=prompt,
                    system=_MARKETING_SYSTEM,
                    temperature=0.75,
                    max_tokens=4000,
                )
                if result and not result.get("stub"):
                    return result, f"openai ({self.ai.openai.model})"
            except Exception as exc:
                logger.warning("OpenAI marketing generation failed: %s", exc)

        # 3. Groq
        if settings.groq_api_key:
            result = self._call_openai_compatible_json(
                messages,
                settings.groq_api_key,
                "https://api.groq.com/openai/v1/chat/completions",
                settings.groq_model,
            )
            if result:
                return result, f"groq ({settings.groq_model})"

        # 4. Deepseek
        if settings.deepseek_api_key:
            result = self._call_openai_compatible_json(
                messages,
                settings.deepseek_api_key,
                "https://api.deepseek.com/v1/chat/completions",
                settings.deepseek_model,
            )
            if result:
                return result, f"deepseek ({settings.deepseek_model})"

        # 5. Grok (xAI)
        if settings.grok_api_key:
            result = self._call_openai_compatible_json(
                messages,
                settings.grok_api_key,
                "https://api.x.ai/v1/chat/completions",
                settings.grok_model,
            )
            if result:
                return result, f"grok ({settings.grok_model})"

        return None, "stub"

    def _get_trending_hooks(
        self,
        *,
        title: str,
        region: str,
        region_label: str,
        target_user: str,
    ) -> list[str]:
        """Get trending hooks for the region. Uses Grok if available (real-time web access)."""
        from app.core.config import get_settings

        settings = get_settings()

        prompt = (
            f'Give me 5 trending content hooks for marketing a product called "{title}" '
            f"to {target_user} in the {region_label} market right now.\n"
            "Format: Return ONLY a JSON array of 5 strings. "
            "Each string is a short hook (under 15 words).\n"
            'Example: ["Hook 1", "Hook 2", "Hook 3", "Hook 4", "Hook 5"]\n\n'
            f"Make them feel current, culturally relevant to {region_label}, and scroll-stopping."
        )

        messages = [{"role": "user", "content": prompt}]

        # Grok first (real-time web access)
        if settings.grok_api_key:
            try:
                raw = self._call_openai_compatible_raw(
                    messages,
                    settings.grok_api_key,
                    "https://api.x.ai/v1/chat/completions",
                    settings.grok_model,
                )
                if raw:
                    parsed = json.loads(raw.strip())
                    if isinstance(parsed, list):
                        return [str(h) for h in parsed[:5]]
            except Exception as exc:
                logger.warning("Grok trending hooks failed: %s", exc)

        # Generic fallback
        return [
            f"You won't believe what {title} just did...",
            f"This changed everything for {target_user}",
            f"POV: You finally found {title}",
            f"Why everyone in {region_label} is talking about {title}",
            f"The {title} challenge — are you in?",
        ]

    def _call_anthropic_json(
        self,
        messages: list[dict],
        api_key: str,
        model: str,
    ) -> dict | None:
        try:
            with httpx.Client(timeout=45) as client:
                resp = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 4000,
                        "system": _MARKETING_SYSTEM,
                        "messages": messages,
                    },
                )
                resp.raise_for_status()
                text = resp.json()["content"][0]["text"]
                text = text.strip()
                if text.startswith("```"):
                    text = text.split("```", 2)[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.rsplit("```", 1)[0]
                return json.loads(text.strip())
        except Exception as exc:
            logger.warning("Anthropic marketing call failed: %s", exc)
            return None

    def _call_openai_compatible_json(
        self,
        messages: list[dict],
        api_key: str,
        endpoint: str,
        model: str,
    ) -> dict | None:
        raw = self._call_openai_compatible_raw(messages, api_key, endpoint, model)
        if not raw:
            return None
        try:
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("```", 2)[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.rsplit("```", 1)[0]
            return json.loads(text.strip())
        except Exception as exc:
            logger.warning("JSON parse failed for %s: %s", endpoint, exc)
            return None

    def _call_openai_compatible_raw(
        self,
        messages: list[dict],
        api_key: str,
        endpoint: str,
        model: str,
    ) -> str | None:
        try:
            with httpx.Client(timeout=45) as client:
                resp = client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": _MARKETING_SYSTEM},
                            *messages,
                        ],
                        "max_tokens": 4000,
                        "temperature": 0.75,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning(
                "OpenAI-compatible marketing call failed (%s): %s", endpoint, exc
            )
            return None
