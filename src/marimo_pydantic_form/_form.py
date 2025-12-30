from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import marimo as mo
from pydantic import BaseModel

from ._pydantic_helper import FieldPath, iter_leaf_fields, unflatten_model

if TYPE_CHECKING:
    from collections.abc import Callable

    from marimo._output.hypertext import Html
    from marimo._plugins.core.web_component import JSONType  # pyright: ignore[reportMissingTypeStubs]
    from marimo._plugins.ui._core.ui_element import UIElement


@dataclass(slots=True)
class PydanticFormBuilder[T: BaseModel]:
    model: type[T]
    ui: dict[str, UIElement[object, object]] = field(default_factory=dict)

    def _default_markdown(self) -> Html:
        lines = [f"### {self.model.__name__} Form"]
        for field_path, _field_info in iter_leaf_fields(self.model):
            lines.append(f"{{{field_path.as_normalized}}}")
            lines.append("")
        return mo.md("\n".join(lines))

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
        field_path_to_ui: dict[FieldPath, UIElement[object, object]] = {}
        leaf_field_paths = {field_path for field_path, _ in iter_leaf_fields(self.model)}
        for field_path_dotted, ui_element in self.ui.items():
            field_path = FieldPath.from_dotted(field_path_dotted)
            if field_path not in leaf_field_paths:
                msg = f"Field path {field_path_dotted} is not a valid leaf field path of model {self.model.__name__}"
                raise ValueError(msg)
            field_path_to_ui[field_path] = ui_element

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
