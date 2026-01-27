from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import marimo as mo
from pydantic import BaseModel

from ._pydantic_helper import FieldPath, iter_leaf_fields, iter_model_structure, unflatten_model
from ._ui_generator import field_name_to_label, generate_ui_element

if TYPE_CHECKING:
    from collections.abc import Callable

    from marimo._output.hypertext import Html
    from marimo._plugins.core.web_component import JSONType  # pyright: ignore[reportMissingTypeStubs]
    from marimo._plugins.ui._core.ui_element import UIElement


@dataclass(slots=True)
class PydanticFormBuilder[T: BaseModel]:
    model: type[T]
    ui: dict[str, UIElement[object, object]] = field(default_factory=dict)
    auto_generate: bool = True

    def _default_markdown(self) -> Html:
        """Generate hierarchical markdown with headers for nested models."""
        lines = [f"### {self.model.__name__} Form", ""]
        nesting_level = 0

        for item in iter_model_structure(self.model):
            if item[0] == "field":
                _, field_path, _field_info = item
                lines.append(f"{{{field_path.as_normalized}}}")
                lines.append("")
            elif item[0] == "nested_start":
                _, field_name, _nested_model = item
                nesting_level += 1
                # Use h4, h5, h6 for nested levels (h3 is the form title)
                header_level = min(3 + nesting_level, 6)
                header = "#" * header_level
                label = field_name_to_label(field_name)
                lines.append(f"{header} {label}")
                lines.append("")
            elif item[0] == "nested_end":
                nesting_level -= 1

        return mo.md("\n".join(lines))

    def _get_ui_elements(self) -> dict[FieldPath, UIElement[object, object]]:
        """Get UI elements for all fields, combining auto-generated and manual overrides.

        Manual overrides take precedence over auto-generated elements.
        """
        field_path_to_ui: dict[FieldPath, UIElement[object, object]] = {}
        leaf_fields = list(iter_leaf_fields(self.model))
        leaf_field_paths = {field_path for field_path, _ in leaf_fields}

        # Validate manual UI paths
        for field_path_dotted in self.ui:
            field_path = FieldPath.from_dotted(field_path_dotted)
            if field_path not in leaf_field_paths:
                msg = f"Field path {field_path_dotted} is not a valid leaf field path of model {self.model.__name__}"
                raise ValueError(msg)

        # Process each field
        for field_path, field_info in leaf_fields:
            dotted = field_path.as_dotted

            if dotted in self.ui:
                # Use manual override
                field_path_to_ui[field_path] = self.ui[dotted]
            elif self.auto_generate:
                # Auto-generate (may raise UnsupportedTypeError)
                ui_element = generate_ui_element(field_path, field_info)
                field_path_to_ui[field_path] = ui_element
            else:
                # No auto-generation, field must be manually specified
                msg = f"No UI element provided for field '{dotted}' and auto_generate is False"
                raise ValueError(msg)

        return field_path_to_ui

    def build(  # noqa: PLR0913
        self,
        *,
        bordered: bool = True,
        loading: bool = False,
        submit_button_label: str = "Submit",
        submit_button_tooltip: str | None = None,
        submit_button_disabled: bool = False,
        clear_on_submit: bool = False,
        show_clear_button: bool = False,
        clear_button_label: str = "Clear",
        clear_button_tooltip: str | None = None,
        validate: Callable[[JSONType | None], str | None] | None = None,
        label: str = "",
        on_change: Callable[[dict[str, object] | None], None] | None = None,
    ) -> mo.ui.form[dict[str, object], dict[str, object]]:
        """Build a Marimo form for the Pydantic model."""
        field_path_to_ui = self._get_ui_elements()

        normalized_field_path_to_ui = {
            field_path.as_normalized: ui_element for field_path, ui_element in field_path_to_ui.items()
        }

        return (
            self._default_markdown()
            .batch(**normalized_field_path_to_ui)
            .form(
                bordered=bordered,
                loading=loading,
                submit_button_label=submit_button_label,
                submit_button_tooltip=submit_button_tooltip,
                submit_button_disabled=submit_button_disabled,
                clear_on_submit=clear_on_submit,
                show_clear_button=show_clear_button,
                clear_button_label=clear_button_label,
                clear_button_tooltip=clear_button_tooltip,
                validate=validate,
                label=label,
                on_change=on_change,
            )
        )

    def parse(self, value: dict[str, object] | None) -> T | None:
        """Parse the form value into the Pydantic model instance.

        The value is expected to be a flattened dictionary with keys as field paths in normalized form.
        """
        if value is None:
            return None

        return unflatten_model(
            self.model,
            {FieldPath.from_normalized(path): v for path, v in value.items()},
        )
