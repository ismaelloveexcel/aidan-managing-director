"""Tests for the UI kit manifest module."""

from __future__ import annotations


from app.planning.ui_kit_manifest import UIComponent, UIKitManifest, generate_ui_kit_manifest


class TestGenerateUiKitManifest:
    """Tests for generate_ui_kit_manifest function."""

    def test_returns_ui_kit_manifest(self) -> None:
        result = generate_ui_kit_manifest()
        assert isinstance(result, UIKitManifest)

    def test_default_theme_is_dark(self) -> None:
        result = generate_ui_kit_manifest()
        assert result.theme == "dark"

    def test_light_theme(self) -> None:
        result = generate_ui_kit_manifest(theme="light")
        assert result.theme == "light"

    def test_has_six_components(self) -> None:
        result = generate_ui_kit_manifest()
        assert len(result.components) == 6

    def test_component_names(self) -> None:
        result = generate_ui_kit_manifest()
        names = {c.name for c in result.components}
        assert "Button" in names
        assert "Card" in names
        assert "Badge" in names
        assert "Input" in names
        assert "ProgressBar" in names
        assert "Alert" in names

    def test_each_component_has_html_template(self) -> None:
        result = generate_ui_kit_manifest()
        for component in result.components:
            assert isinstance(component.html_template, str)
            assert len(component.html_template) > 0

    def test_each_component_has_css(self) -> None:
        result = generate_ui_kit_manifest()
        for component in result.components:
            assert isinstance(component.css, str)
            assert len(component.css) > 0

    def test_each_component_has_variants(self) -> None:
        result = generate_ui_kit_manifest()
        for component in result.components:
            assert isinstance(component.variants, list)
            assert len(component.variants) > 0

    def test_css_variables_present(self) -> None:
        result = generate_ui_kit_manifest()
        assert isinstance(result.css_variables, dict)
        assert len(result.css_variables) > 0

    def test_dark_theme_has_dark_background(self) -> None:
        result = generate_ui_kit_manifest(theme="dark")
        bg = result.css_variables.get("--color-background", "")
        assert bg  # non-empty

    def test_light_theme_has_different_bg_than_dark(self) -> None:
        dark = generate_ui_kit_manifest(theme="dark")
        light = generate_ui_kit_manifest(theme="light")
        assert dark.css_variables.get("--color-background") != light.css_variables.get("--color-background")

    def test_version_is_set(self) -> None:
        result = generate_ui_kit_manifest()
        assert result.version
        assert "." in result.version  # semver-like

    def test_button_has_primary_variant(self) -> None:
        result = generate_ui_kit_manifest()
        button = next(c for c in result.components if c.name == "Button")
        variant_names = [v["name"] for v in button.variants]
        assert "primary" in variant_names

    def test_badge_has_all_status_variants(self) -> None:
        result = generate_ui_kit_manifest()
        badge = next(c for c in result.components if c.name == "Badge")
        variant_names = {v["name"] for v in badge.variants}
        assert {"success", "warning", "danger"}.issubset(variant_names)

    def test_alert_has_all_status_variants(self) -> None:
        result = generate_ui_kit_manifest()
        alert = next(c for c in result.components if c.name == "Alert")
        variant_names = {v["name"] for v in alert.variants}
        assert {"success", "warning", "danger", "info"}.issubset(variant_names)

    def test_css_variables_use_double_dash_prefix(self) -> None:
        result = generate_ui_kit_manifest()
        for key in result.css_variables:
            assert key.startswith("--"), f"CSS variable '{key}' should start with '--'"


class TestUIComponent:
    """Tests for UIComponent Pydantic model."""

    def test_valid_component(self) -> None:
        comp = UIComponent(
            name="TestComp",
            html_template="<div>{content}</div>",
            css=".test{color:red}",
            variants=[{"name": "default", "description": "Default variant"}],
        )
        assert comp.name == "TestComp"
        assert comp.variants[0]["name"] == "default"

    def test_default_variants_empty(self) -> None:
        comp = UIComponent(
            name="TestComp",
            html_template="<div/>",
            css="",
        )
        assert comp.variants == []
