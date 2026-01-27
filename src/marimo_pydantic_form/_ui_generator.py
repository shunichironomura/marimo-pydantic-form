"""UI element generator for Pydantic model fields."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from enum import Enum
from inspect import isclass
from typing import TYPE_CHECKING, Any, Literal, Union, get_args, get_origin

import annotated_types
import marimo as mo
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

if TYPE_CHECKING:
    from marimo._plugins.ui._core.ui_element import UIElement
    from pydantic.fields import FieldInfo

    from ._pydantic_helper import FieldPath


class UnsupportedTypeError(Exception):
    """Raised when a field type cannot be auto-generated."""

    def __init__(self, field_path: FieldPath, annotation: type) -> None:
        self.field_path = field_path
        self.annotation = annotation
        super().__init__(
            f"Cannot auto-generate UI for field '{field_path.as_dotted}' "
            f"with type '{annotation}'. Please provide a manual UI element.",
        )


# --- Type Detection Utilities ---


def unwrap_optional(annotation: type) -> tuple[type, bool]:
    """Unwrap Optional types.

    If annotation is Optional[T] (Union[T, None]), return (T, True).
    Otherwise return (annotation, False).
    """
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == len(args) - 1:
            if len(non_none_args) == 1:
                return (non_none_args[0], True)
            # Multi-type union with None - still optional but complex
            # Return the original union without None for further processing
            return (Union[tuple(non_none_args)], True)  # type: ignore[return-value]  # noqa: UP007
    return (annotation, False)


def is_literal_type(annotation: type) -> bool:
    """Check if annotation is a Literal type."""
    return get_origin(annotation) is Literal


def is_enum_type(annotation: type) -> bool:
    """Check if annotation is an Enum subclass."""
    return isclass(annotation) and issubclass(annotation, Enum)


def is_union_type(annotation: type) -> bool:
    """Check if annotation is a Union type (excluding Optional which is Union[T, None])."""
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        # It's a "real" union if there's no None or if there are multiple non-None types
        non_none_args = [arg for arg in args if arg is not type(None)]
        return len(non_none_args) > 1
    return False


def is_list_type(annotation: type) -> bool:
    """Check if annotation is a list type."""
    origin = get_origin(annotation)
    return origin is list


def is_nested_model(annotation: type) -> bool:
    """Check if annotation is a nested Pydantic BaseModel."""
    return isclass(annotation) and issubclass(annotation, BaseModel)


# --- Constraint Extraction ---


@dataclass
class ExtractedConstraints:
    """Container for extracted Pydantic field constraints."""

    gt: float | int | None = None  # greater than (exclusive)
    ge: float | int | None = None  # greater than or equal (inclusive)
    lt: float | int | None = None  # less than (exclusive)
    le: float | int | None = None  # less than or equal (inclusive)
    min_length: int | None = None
    max_length: int | None = None


def extract_constraints(field_info: FieldInfo) -> ExtractedConstraints:
    """Extract constraints from FieldInfo.metadata."""
    constraints = ExtractedConstraints()

    for meta in field_info.metadata:
        if isinstance(meta, annotated_types.Gt):
            constraints.gt = meta.gt  # type: ignore[assignment]
        elif isinstance(meta, annotated_types.Ge):
            constraints.ge = meta.ge  # type: ignore[assignment]
        elif isinstance(meta, annotated_types.Lt):
            constraints.lt = meta.lt  # type: ignore[assignment]
        elif isinstance(meta, annotated_types.Le):
            constraints.le = meta.le  # type: ignore[assignment]
        elif isinstance(meta, annotated_types.MinLen):
            constraints.min_length = meta.min_length
        elif isinstance(meta, annotated_types.MaxLen):
            constraints.max_length = meta.max_length

    return constraints


# --- Label Generation ---


def field_name_to_label(field_name: str) -> str:
    """Convert a field name to a human-readable label.

    Examples:
        'user_name' -> 'User Name'
        'firstName' -> 'First Name'
        'HTTPResponse' -> 'HTTP Response'

    """
    # Handle snake_case
    name = field_name.replace("_", " ")
    # Handle camelCase and PascalCase
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    # Handle consecutive caps (e.g., HTTPResponse -> HTTP Response)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    return name.title()


def generate_label(field_path: FieldPath, field_info: FieldInfo) -> str:
    """Generate a label for a field.

    Uses field's title if available, otherwise generates from the leaf field name.
    """
    if field_info.title:
        return field_info.title
    # Use the last part of the field path as the field name
    field_name = field_path.parts[-1]
    return field_name_to_label(field_name)


# --- UI Factory Functions ---


def create_number_ui(
    field_path: FieldPath,
    field_info: FieldInfo,
    constraints: ExtractedConstraints,
    *,
    is_optional: bool,  # noqa: ARG001
    base_type: type,
) -> mo.ui.number:
    """Create a mo.ui.number element for int/float fields."""
    label = generate_label(field_path, field_info)

    # Determine start/stop from constraints
    start: float | int | None = None
    stop: float | int | None = None

    if constraints.ge is not None:
        start = constraints.ge
    elif constraints.gt is not None:
        # For exclusive bound, add 1 for int
        start = int(constraints.gt) + 1 if base_type is int else constraints.gt

    if constraints.le is not None:
        stop = constraints.le
    elif constraints.lt is not None:
        stop = int(constraints.lt) - 1 if base_type is int else constraints.lt

    # Determine step based on type
    step: float | int | None = 1 if base_type is int else None

    # Determine default value
    default_value: float | int | None = None
    if field_info.default is not None and field_info.default is not PydanticUndefined:
        default_value = field_info.default  # type: ignore[assignment]
    elif start is not None:
        default_value = start
    elif stop is not None:
        default_value = stop

    return mo.ui.number(
        start=start,
        stop=stop,
        step=step,
        value=default_value,
        label=label,
    )


def create_text_ui(
    field_path: FieldPath,
    field_info: FieldInfo,
    constraints: ExtractedConstraints,
    *,
    is_optional: bool,  # noqa: ARG001
) -> mo.ui.text:
    """Create a mo.ui.text element for str fields."""
    label = generate_label(field_path, field_info)

    default_value = ""
    if field_info.default is not None and field_info.default is not PydanticUndefined:
        default_value = field_info.default  # type: ignore[assignment]

    return mo.ui.text(
        value=default_value,
        max_length=constraints.max_length,
        label=label,
    )


def create_checkbox_ui(
    field_path: FieldPath,
    field_info: FieldInfo,
    *,
    is_optional: bool,  # noqa: ARG001
) -> mo.ui.checkbox:
    """Create a mo.ui.checkbox element for bool fields."""
    label = generate_label(field_path, field_info)

    default_value = False
    if field_info.default is not None and field_info.default is not PydanticUndefined:
        default_value = field_info.default  # type: ignore[assignment]

    return mo.ui.checkbox(
        value=default_value,
        label=label,
    )


def create_dropdown_ui(
    field_path: FieldPath,
    field_info: FieldInfo,
    options: dict[str, Any],
    *,
    is_optional: bool,
) -> mo.ui.dropdown:
    """Create a mo.ui.dropdown element for Literal/Enum fields."""
    label = generate_label(field_path, field_info)

    default_value: str | None = None
    if field_info.default is not None and field_info.default is not PydanticUndefined:
        # Find the key for the default value
        for key, val in options.items():
            if val == field_info.default:
                default_value = key
                break

    # If not optional and no default, use the first option
    if not is_optional and default_value is None and options:
        default_value = next(iter(options.keys()))

    return mo.ui.dropdown(
        options=options,
        value=default_value,
        allow_select_none=is_optional,
        label=label,
    )


def create_date_ui(
    field_path: FieldPath,
    field_info: FieldInfo,
    *,
    is_optional: bool,  # noqa: ARG001
) -> mo.ui.date:
    """Create a mo.ui.date element for date fields."""
    label = generate_label(field_path, field_info)

    default_value: dt.date | None = None
    if field_info.default is not None and field_info.default is not PydanticUndefined:
        default_value = field_info.default  # type: ignore[assignment]

    return mo.ui.date(
        value=default_value,
        label=label,
    )


def create_datetime_ui(
    field_path: FieldPath,
    field_info: FieldInfo,
    *,
    is_optional: bool,  # noqa: ARG001
) -> mo.ui.datetime:
    """Create a mo.ui.datetime element for datetime fields."""
    label = generate_label(field_path, field_info)

    default_value: dt.datetime | None = None
    if field_info.default is not None and field_info.default is not PydanticUndefined:
        default_value = field_info.default  # type: ignore[assignment]

    return mo.ui.datetime(
        value=default_value,
        label=label,
    )


# --- Main Generator ---


def generate_ui_element(  # noqa: C901, PLR0911
    field_path: FieldPath,
    field_info: FieldInfo,
) -> UIElement[object, object]:
    """Generate an appropriate marimo UI element for a given field.

    Raises:
        UnsupportedTypeError: If the field type cannot be auto-generated.

    """
    annotation = field_info.annotation

    # Handle Optional types
    inner_type, is_optional = unwrap_optional(annotation)

    # Check for unsupported types first
    if is_union_type(inner_type):
        raise UnsupportedTypeError(field_path, annotation)

    if is_list_type(inner_type):
        raise UnsupportedTypeError(field_path, annotation)

    if is_nested_model(inner_type):
        # Nested models should be handled by iter_leaf_fields, not here
        raise UnsupportedTypeError(field_path, annotation)

    # Extract constraints
    constraints = extract_constraints(field_info)

    # Type dispatch
    if inner_type is int:
        return create_number_ui(field_path, field_info, constraints, is_optional=is_optional, base_type=int)

    if inner_type is float:
        return create_number_ui(field_path, field_info, constraints, is_optional=is_optional, base_type=float)

    if inner_type is str:
        return create_text_ui(field_path, field_info, constraints, is_optional=is_optional)

    if inner_type is bool:
        return create_checkbox_ui(field_path, field_info, is_optional=is_optional)

    if is_literal_type(inner_type):
        literal_values = get_args(inner_type)
        # Create options dict: display value -> actual value
        options = {str(v): v for v in literal_values}
        return create_dropdown_ui(field_path, field_info, options, is_optional=is_optional)

    if is_enum_type(inner_type):
        # For enums, use member.name as key, member as value
        options = {member.name: member for member in inner_type}  # type: ignore[var-annotated]
        return create_dropdown_ui(field_path, field_info, options, is_optional=is_optional)

    if inner_type is dt.date:
        return create_date_ui(field_path, field_info, is_optional=is_optional)

    if inner_type is dt.datetime:
        return create_datetime_ui(field_path, field_info, is_optional=is_optional)

    # Unsupported type
    raise UnsupportedTypeError(field_path, annotation)
