"""Tests for share template generation and distribution route."""

import pytest
from fastapi.testclient import TestClient

from app.planning.share_templates import ShareMessageBundle, generate_share_messages
from main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DEFAULT_KWARGS = {
    "title": "TaskFlow",
    "url": "https://taskflow.app",
    "description": "Automate your team's workflow in minutes",
    "target_user": "project managers",
    "cta": "Try it free",
}


@pytest.fixture()
def bundle() -> ShareMessageBundle:
    return generate_share_messages(**_DEFAULT_KWARGS)


# ---------------------------------------------------------------------------
# Unit tests – generate_share_messages
# ---------------------------------------------------------------------------


def test_returns_share_message_bundle(bundle: ShareMessageBundle) -> None:
    assert isinstance(bundle, ShareMessageBundle)


def test_twitter_within_280_chars(bundle: ShareMessageBundle) -> None:
    assert len(bundle.twitter) <= 280


def test_twitter_contains_url(bundle: ShareMessageBundle) -> None:
    assert "https://taskflow.app" in bundle.twitter


def test_twitter_contains_title(bundle: ShareMessageBundle) -> None:
    assert "TaskFlow" in bundle.twitter


def test_sms_within_160_chars(bundle: ShareMessageBundle) -> None:
    assert len(bundle.sms) <= 160


def test_sms_contains_url(bundle: ShareMessageBundle) -> None:
    assert "https://taskflow.app" in bundle.sms


def test_linkedin_contains_url(bundle: ShareMessageBundle) -> None:
    assert "https://taskflow.app" in bundle.linkedin


def test_linkedin_professional_tone(bundle: ShareMessageBundle) -> None:
    # LinkedIn message should mention the target user and title
    assert "project managers" in bundle.linkedin
    assert "TaskFlow" in bundle.linkedin


def test_whatsapp_contains_emoji(bundle: ShareMessageBundle) -> None:
    # WhatsApp messages should include at least one emoji
    has_emoji = any(ord(c) > 127 for c in bundle.whatsapp)
    assert has_emoji


def test_whatsapp_contains_url(bundle: ShareMessageBundle) -> None:
    assert "https://taskflow.app" in bundle.whatsapp


def test_email_subject_contains_title(bundle: ShareMessageBundle) -> None:
    assert "TaskFlow" in bundle.email_subject


def test_email_subject_contains_cta(bundle: ShareMessageBundle) -> None:
    assert "Try it free" in bundle.email_subject


def test_email_body_contains_url(bundle: ShareMessageBundle) -> None:
    assert "https://taskflow.app" in bundle.email_body


def test_email_body_contains_target_user(bundle: ShareMessageBundle) -> None:
    assert "project managers" in bundle.email_body


def test_reddit_title_contains_title(bundle: ShareMessageBundle) -> None:
    assert "TaskFlow" in bundle.reddit_title


def test_reddit_title_contains_target_user(bundle: ShareMessageBundle) -> None:
    assert "project managers" in bundle.reddit_title


def test_product_hunt_tagline_within_60_chars(bundle: ShareMessageBundle) -> None:
    assert len(bundle.product_hunt_tagline) <= 60


def test_product_hunt_tagline_non_empty(bundle: ShareMessageBundle) -> None:
    assert bundle.product_hunt_tagline.strip() != ""


def test_custom_cta_in_messages() -> None:
    bundle = generate_share_messages(
        title="CodeBot",
        url="https://codebot.dev",
        description="AI-powered code reviews",
        target_user="developers",
        cta="Start for free",
    )
    assert "Start for free" in bundle.email_subject


def test_long_description_truncated_in_twitter() -> None:
    long_desc = "A" * 300
    bundle = generate_share_messages(
        title="X",
        url="https://x.com",
        description=long_desc,
        target_user="everyone",
        cta="Go",
    )
    assert len(bundle.twitter) <= 280


def test_long_description_truncated_in_sms() -> None:
    long_desc = "B" * 200
    bundle = generate_share_messages(
        title="Y",
        url="https://y.com",
        description=long_desc,
        target_user="users",
        cta="Click",
    )
    assert len(bundle.sms) <= 160


# ---------------------------------------------------------------------------
# Route tests – POST /api/distribution/share-messages
# ---------------------------------------------------------------------------

_client = TestClient(app, raise_server_exceptions=True)
_HEADERS = {"X-API-Key": "test-api-key"}


def test_share_messages_route_returns_200() -> None:
    resp = _client.post(
        "/api/distribution/share-messages",
        json={
            "title": "TaskFlow",
            "url": "https://taskflow.app",
            "description": "Automate your team's workflow in minutes",
            "target_user": "project managers",
            "cta": "Try it free",
        },
        headers=_HEADERS,
    )
    assert resp.status_code == 200


def test_share_messages_route_response_structure() -> None:
    resp = _client.post(
        "/api/distribution/share-messages",
        json={
            "title": "TaskFlow",
            "url": "https://taskflow.app",
            "description": "Automate your team's workflow in minutes",
            "target_user": "project managers",
        },
        headers=_HEADERS,
    )
    data = resp.json()
    assert "twitter" in data
    assert "linkedin" in data
    assert "whatsapp" in data
    assert "email_subject" in data
    assert "email_body" in data
    assert "sms" in data
    assert "reddit_title" in data
    assert "product_hunt_tagline" in data


def test_share_messages_route_invalid_url() -> None:
    resp = _client.post(
        "/api/distribution/share-messages",
        json={
            "title": "Test",
            "url": "not-a-url",
            "description": "Something",
            "target_user": "devs",
        },
        headers=_HEADERS,
    )
    assert resp.status_code == 422


def test_share_messages_route_missing_required_fields() -> None:
    resp = _client.post(
        "/api/distribution/share-messages",
        json={"title": "Only title"},
        headers=_HEADERS,
    )
    assert resp.status_code == 422


def test_share_messages_route_default_cta() -> None:
    resp = _client.post(
        "/api/distribution/share-messages",
        json={
            "title": "MyApp",
            "url": "https://myapp.io",
            "description": "A great app",
            "target_user": "users",
        },
        headers=_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    # default CTA is "Try it free"
    assert "Try it free" in data["email_subject"]
