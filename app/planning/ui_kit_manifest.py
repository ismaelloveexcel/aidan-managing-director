"""
ui_kit_manifest.py – Shared UI component manifest for Factory templates.

Defines reusable UI components (Button, Card, Badge, Input, ProgressBar, Alert)
that the Factory's inject_brief.py can inject into generated product templates.
Each component includes HTML template, CSS, and variant definitions.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class UIComponent(BaseModel):
    """Definition of a single reusable UI component."""

    name: str
    html_template: str
    css: str
    variants: list[dict[str, Any]] = Field(default_factory=list)


class UIKitManifest(BaseModel):
    """Complete UI kit manifest for Factory template injection."""

    theme: str
    components: list[UIComponent] = Field(default_factory=list)
    css_variables: dict[str, str] = Field(default_factory=dict)
    version: str = _VERSION


# ---------------------------------------------------------------------------
# CSS variables (mapped to design tokens)
# ---------------------------------------------------------------------------

_DARK_CSS_VARS: dict[str, str] = {
    "--color-primary": "#5b6ef7",
    "--color-primary-hover": "#4a5ce6",
    "--color-surface": "#1a1a2e",
    "--color-surface-2": "#111111",
    "--color-background": "#0a0a0a",
    "--color-text": "#e0e0e0",
    "--color-text-muted": "#888888",
    "--color-success": "#16a34a",
    "--color-warning": "#d97706",
    "--color-danger": "#dc2626",
    "--color-border": "#333333",
    "--color-border-focus": "#5b6ef7",
    "--radius-sm": "4px",
    "--radius-md": "8px",
    "--radius-lg": "12px",
    "--font-family": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    "--font-size-xs": "0.75rem",
    "--font-size-sm": "0.85rem",
    "--font-size-base": "1rem",
    "--font-size-lg": "1.2rem",
    "--font-size-xl": "1.5rem",
    "--spacing-xs": "0.25rem",
    "--spacing-sm": "0.5rem",
    "--spacing-md": "1rem",
    "--spacing-lg": "1.5rem",
    "--spacing-xl": "2rem",
}

_LIGHT_CSS_VARS: dict[str, str] = {
    "--color-primary": "#4f5ed6",
    "--color-primary-hover": "#3e4dc5",
    "--color-surface": "#ffffff",
    "--color-surface-2": "#f5f5f5",
    "--color-background": "#f0f0f0",
    "--color-text": "#111111",
    "--color-text-muted": "#555555",
    "--color-success": "#15803d",
    "--color-warning": "#b45309",
    "--color-danger": "#b91c1c",
    "--color-border": "#dddddd",
    "--color-border-focus": "#4f5ed6",
    "--radius-sm": "4px",
    "--radius-md": "8px",
    "--radius-lg": "12px",
    "--font-family": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    "--font-size-xs": "0.75rem",
    "--font-size-sm": "0.85rem",
    "--font-size-base": "1rem",
    "--font-size-lg": "1.2rem",
    "--font-size-xl": "1.5rem",
    "--spacing-xs": "0.25rem",
    "--spacing-sm": "0.5rem",
    "--spacing-md": "1rem",
    "--spacing-lg": "1.5rem",
    "--spacing-xl": "2rem",
}


# ---------------------------------------------------------------------------
# Component definitions
# ---------------------------------------------------------------------------

_BUTTON = UIComponent(
    name="Button",
    html_template=(
        '<button class="btn btn-{variant}">{label}</button>'
    ),
    css=(
        ".btn{display:inline-flex;align-items:center;justify-content:center;"
        "padding:.6rem 1.2rem;border:none;border-radius:var(--radius-md);"
        "font-size:var(--font-size-base);font-weight:600;cursor:pointer;"
        "transition:background .2s,opacity .2s;font-family:var(--font-family)}"
        ".btn:disabled{opacity:.5;cursor:not-allowed}"
        ".btn-primary{background:var(--color-primary);color:#fff}"
        ".btn-primary:hover{background:var(--color-primary-hover)}"
        ".btn-secondary{background:var(--color-surface);color:var(--color-text);"
        "border:1px solid var(--color-border)}"
        ".btn-secondary:hover{border-color:var(--color-primary)}"
        ".btn-ghost{background:transparent;color:var(--color-primary);"
        "border:1px solid var(--color-primary)}"
        ".btn-ghost:hover{background:var(--color-primary);color:#fff}"
    ),
    variants=[
        {"name": "primary", "class": "btn-primary", "description": "Primary call-to-action"},
        {"name": "secondary", "class": "btn-secondary", "description": "Secondary action"},
        {"name": "ghost", "class": "btn-ghost", "description": "Low-emphasis action"},
    ],
)

_CARD = UIComponent(
    name="Card",
    html_template=(
        '<div class="card card-{variant}">{content}</div>'
    ),
    css=(
        ".card{border-radius:var(--radius-lg);padding:var(--spacing-lg);"
        "font-family:var(--font-family)}"
        ".card-elevated{background:var(--color-surface);"
        "box-shadow:0 4px 16px rgba(0,0,0,.35);border:1px solid var(--color-border)}"
        ".card-flat{background:var(--color-surface-2);"
        "border:1px solid var(--color-border)}"
    ),
    variants=[
        {"name": "elevated", "class": "card-elevated", "description": "Elevated card with shadow"},
        {"name": "flat", "class": "card-flat", "description": "Flat card without shadow"},
    ],
)

_BADGE = UIComponent(
    name="Badge",
    html_template=(
        '<span class="badge badge-{variant}">{label}</span>'
    ),
    css=(
        ".badge{display:inline-block;padding:.2rem .6rem;"
        "border-radius:var(--radius-sm);font-size:var(--font-size-xs);"
        "font-weight:700;font-family:var(--font-family)}"
        ".badge-success{background:var(--color-success);color:#fff}"
        ".badge-warning{background:var(--color-warning);color:#fff}"
        ".badge-danger{background:var(--color-danger);color:#fff}"
        ".badge-neutral{background:var(--color-border);color:var(--color-text)}"
    ),
    variants=[
        {"name": "success", "class": "badge-success", "description": "Positive / approved"},
        {"name": "warning", "class": "badge-warning", "description": "Warning / hold"},
        {"name": "danger", "class": "badge-danger", "description": "Error / rejected"},
        {"name": "neutral", "class": "badge-neutral", "description": "Neutral information"},
    ],
)

_INPUT = UIComponent(
    name="Input",
    html_template=(
        '<input class="input" type="{type}" placeholder="{placeholder}" />'
    ),
    css=(
        ".input{width:100%;padding:.6rem .8rem;"
        "border:1px solid var(--color-border);"
        "border-radius:var(--radius-md);"
        "background:var(--color-surface-2);"
        "color:var(--color-text);"
        "font-size:var(--font-size-base);"
        "font-family:var(--font-family);outline:none}"
        ".input:focus{border-color:var(--color-border-focus)}"
    ),
    variants=[
        {"name": "text", "type": "text", "description": "Standard text input"},
        {"name": "email", "type": "email", "description": "Email address input"},
        {"name": "password", "type": "password", "description": "Password input"},
    ],
)

_PROGRESS_BAR = UIComponent(
    name="ProgressBar",
    html_template=(
        '<div class="progress-bar">'
        '<div class="progress-fill progress-{variant}" style="width:{percent}%"></div>'
        '</div>'
    ),
    css=(
        ".progress-bar{height:8px;background:var(--color-border);"
        "border-radius:var(--radius-sm);overflow:hidden}"
        ".progress-fill{height:100%;border-radius:var(--radius-sm);"
        "transition:width .4s ease}"
        ".progress-success{background:var(--color-success)}"
        ".progress-warning{background:var(--color-warning)}"
        ".progress-danger{background:var(--color-danger)}"
        ".progress-primary{background:var(--color-primary)}"
    ),
    variants=[
        {"name": "success", "class": "progress-success", "description": "Green progress"},
        {"name": "warning", "class": "progress-warning", "description": "Amber progress"},
        {"name": "danger", "class": "progress-danger", "description": "Red progress"},
        {"name": "primary", "class": "progress-primary", "description": "Primary accent progress"},
    ],
)

_ALERT = UIComponent(
    name="Alert",
    html_template=(
        '<div class="alert alert-{variant}"><strong>{title}</strong> {message}</div>'
    ),
    css=(
        ".alert{padding:var(--spacing-sm) var(--spacing-md);"
        "border-radius:var(--radius-md);font-size:var(--font-size-sm);"
        "font-family:var(--font-family);margin:.5rem 0}"
        ".alert-success{background:#0a2a0a;border:1px solid var(--color-success);"
        "color:#86efac}"
        ".alert-warning{background:#2a2a0a;border:1px solid var(--color-warning);"
        "color:#fde68a}"
        ".alert-danger{background:#2a0a0a;border:1px solid var(--color-danger);"
        "color:#fca5a5}"
        ".alert-info{background:#0a0a2a;border:1px solid var(--color-primary);"
        "color:#a5b4fc}"
    ),
    variants=[
        {"name": "success", "class": "alert-success", "description": "Success notification"},
        {"name": "warning", "class": "alert-warning", "description": "Warning notification"},
        {"name": "danger", "class": "alert-danger", "description": "Error notification"},
        {"name": "info", "class": "alert-info", "description": "Informational message"},
    ],
)

_COMPONENTS = [_BUTTON, _CARD, _BADGE, _INPUT, _PROGRESS_BAR, _ALERT]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_ui_kit_manifest(theme: Literal["dark", "light"] = "dark") -> UIKitManifest:
    """Generate the UI kit manifest for a given theme.

    Returns a complete manifest with all reusable components and CSS variables.
    The Factory's ``inject_brief.py`` reads this manifest to inject components
    into generated product templates.

    Args:
        theme: ``"dark"`` (default) or ``"light"``.

    Returns:
        UIKitManifest with theme, components, css_variables, and version.
    """
    css_vars = _DARK_CSS_VARS if theme == "dark" else _LIGHT_CSS_VARS

    return UIKitManifest(
        theme=theme,
        components=list(_COMPONENTS),
        css_variables=css_vars,
        version=_VERSION,
    )
