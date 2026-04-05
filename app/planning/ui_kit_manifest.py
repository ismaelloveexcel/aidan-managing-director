"""
ui_kit_manifest.py – Shared UI component manifest for factory-generated products.

Defines the specification of reusable UI components that the Factory can
inject into generated product UIs.  ``inject_brief.py`` in the Factory
reads this manifest to customise generated interfaces with consistent,
premium components.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UIComponent(BaseModel):
    """Specification for a single reusable UI component."""

    name: str = Field(description="Component name (PascalCase)")
    description: str = Field(description="What the component does")
    tailwind_classes: str = Field(description="Default Tailwind CSS class string")
    variants: list[str] = Field(default_factory=list, description="Available style variants")
    props: list[str] = Field(default_factory=list, description="Configurable props / attributes")


class UIKitManifest(BaseModel):
    """Manifest of all shared UI components available to the Factory."""

    version: str = Field(description="Manifest schema version")
    components: list[UIComponent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Component definitions
# ---------------------------------------------------------------------------

_COMPONENTS: list[UIComponent] = [
    UIComponent(
        name="Button",
        description="Primary action button with hover, focus, and disabled states.",
        tailwind_classes=(
            "inline-flex items-center justify-center px-4 py-2 rounded-lg font-semibold "
            "text-sm transition-all duration-200 focus:outline-none focus:ring-2 "
            "focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        ),
        variants=["primary", "secondary", "danger", "ghost", "outline"],
        props=["label", "onClick", "disabled", "loading", "size", "variant", "icon"],
    ),
    UIComponent(
        name="Card",
        description="Container card with border, shadow, and padding for content grouping.",
        tailwind_classes=(
            "bg-surface border border-border rounded-xl p-6 shadow-sm "
            "transition-shadow hover:shadow-md"
        ),
        variants=["default", "elevated", "flat", "highlighted"],
        props=["title", "subtitle", "footer", "padding", "variant", "onClick"],
    ),
    UIComponent(
        name="Badge",
        description="Inline status indicator or label tag.",
        tailwind_classes=(
            "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
        ),
        variants=["success", "warning", "danger", "info", "neutral"],
        props=["label", "variant", "dot", "dismissible"],
    ),
    UIComponent(
        name="Input",
        description="Text input field with label, placeholder, and validation states.",
        tailwind_classes=(
            "block w-full px-3 py-2 border border-border rounded-lg text-sm "
            "bg-background placeholder-muted focus:outline-none focus:ring-2 "
            "focus:ring-primary focus:border-transparent"
        ),
        variants=["default", "error", "success", "disabled"],
        props=["label", "placeholder", "value", "onChange", "type", "error", "required", "disabled"],
    ),
    UIComponent(
        name="Alert",
        description="Contextual alert banner for status messages and notifications.",
        tailwind_classes=(
            "flex items-start gap-3 p-4 rounded-lg border text-sm font-medium"
        ),
        variants=["info", "success", "warning", "error"],
        props=["message", "title", "variant", "dismissible", "icon"],
    ),
    UIComponent(
        name="Modal",
        description="Overlay dialog for confirmations, forms, and focused interactions.",
        tailwind_classes=(
            "fixed inset-0 z-50 flex items-center justify-center p-4 "
            "bg-black/50 backdrop-blur-sm"
        ),
        variants=["sm", "md", "lg", "fullscreen"],
        props=["title", "open", "onClose", "size", "footer", "closeOnBackdrop"],
    ),
    UIComponent(
        name="Toast",
        description="Transient notification that auto-dismisses after a timeout.",
        tailwind_classes=(
            "flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium "
            "min-w-64 max-w-sm pointer-events-auto"
        ),
        variants=["success", "error", "warning", "info"],
        props=["message", "variant", "duration", "position", "onDismiss"],
    ),
]


def get_ui_kit_manifest() -> UIKitManifest:
    """Return the current shared UI kit component manifest.

    Returns:
        ``UIKitManifest`` containing all component specifications the
        Factory can inject into generated product UIs.
    """
    return UIKitManifest(
        version="1.0.0",
        components=_COMPONENTS,
    )
