"""marimo-pydantic-form package."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, TypeVar

import marimo as mo
from pydantic import BaseModel

if TYPE_CHECKING:
    from marimo._plugins.core.web_component import JSONType


@dataclass(slots=True)
class PydanticFormBuilder[T: BaseModel]:
    model: type[T]

    def build(
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
        on_change: Callable[[T | None], None] | None = None,
    ) -> mo.ui.form[T]:
        raise NotImplementedError
