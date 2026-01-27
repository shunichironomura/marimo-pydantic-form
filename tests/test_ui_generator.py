"""Tests for UI element auto-generation."""

import datetime as dt
from enum import Enum
from typing import Literal

import marimo as mo
import pytest
from pydantic import BaseModel, Field

from marimo_pydantic_form import PydanticFormBuilder, UnsupportedTypeError
from marimo_pydantic_form._pydantic_helper import FieldPath, iter_model_structure
from marimo_pydantic_form._ui_generator import (
    ExtractedConstraints,
    extract_constraints,
    field_name_to_label,
    generate_label,
    generate_ui_element,
    is_enum_type,
    is_list_type,
    is_literal_type,
    is_union_type,
    unwrap_optional,
)

# --- Type Detection Tests ---


def test_unwrap_optional_with_optional() -> None:
    inner, is_optional = unwrap_optional(int | None)
    assert inner is int
    assert is_optional is True


def test_unwrap_optional_without_optional() -> None:
    inner, is_optional = unwrap_optional(int)
    assert inner is int
    assert is_optional is False


def test_unwrap_optional_with_union_none() -> None:
    inner, is_optional = unwrap_optional(str | None)
    assert inner is str
    assert is_optional is True


def test_is_literal_type() -> None:
    assert is_literal_type(Literal["a", "b"]) is True
    assert is_literal_type(str) is False
    assert is_literal_type(int) is False


def test_is_enum_type() -> None:
    class Color(Enum):
        RED = "red"
        GREEN = "green"

    assert is_enum_type(Color) is True
    assert is_enum_type(str) is False
    assert is_enum_type(int) is False


def test_is_union_type() -> None:
    assert is_union_type(int | str) is True
    assert is_union_type(int | None) is False  # Optional is not a "real" union
    assert is_union_type(int) is False


def test_is_list_type() -> None:
    assert is_list_type(list[int]) is True
    assert is_list_type(list[str]) is True
    assert is_list_type(int) is False
    assert is_list_type(str) is False


# --- Constraint Extraction Tests ---


def test_extract_constraints_with_bounds() -> None:
    class Model(BaseModel):
        value: int = Field(ge=0, le=100)

    field_info = Model.model_fields["value"]
    constraints = extract_constraints(field_info)
    assert constraints.ge == 0
    assert constraints.le == 100
    assert constraints.gt is None
    assert constraints.lt is None


def test_extract_constraints_with_exclusive_bounds() -> None:
    class Model(BaseModel):
        value: float = Field(gt=0.0, lt=1.0)

    field_info = Model.model_fields["value"]
    constraints = extract_constraints(field_info)
    assert constraints.gt == 0.0
    assert constraints.lt == 1.0
    assert constraints.ge is None
    assert constraints.le is None


def test_extract_constraints_with_string_length() -> None:
    class Model(BaseModel):
        name: str = Field(min_length=1, max_length=50)

    field_info = Model.model_fields["name"]
    constraints = extract_constraints(field_info)
    assert constraints.min_length == 1
    assert constraints.max_length == 50


def test_extract_constraints_empty() -> None:
    class Model(BaseModel):
        value: int

    field_info = Model.model_fields["value"]
    constraints = extract_constraints(field_info)
    assert constraints == ExtractedConstraints()


# --- Label Generation Tests ---


def test_field_name_to_label_snake_case() -> None:
    assert field_name_to_label("user_name") == "User Name"
    assert field_name_to_label("first_name") == "First Name"
    assert field_name_to_label("email_address") == "Email Address"


def test_field_name_to_label_camel_case() -> None:
    assert field_name_to_label("userName") == "User Name"
    assert field_name_to_label("firstName") == "First Name"


def test_field_name_to_label_pascal_case() -> None:
    assert field_name_to_label("UserName") == "User Name"


def test_field_name_to_label_with_acronyms() -> None:
    # Note: .title() converts to title case, so HTTP becomes Http
    assert field_name_to_label("HTTPResponse") == "Http Response"
    assert field_name_to_label("userID") == "User Id"


def test_generate_label_uses_title() -> None:
    class Model(BaseModel):
        value: int = Field(title="Custom Title")

    field_info = Model.model_fields["value"]
    field_path = FieldPath(("value",))
    label = generate_label(field_path, field_info)
    assert label == "Custom Title"


def test_generate_label_uses_field_name() -> None:
    class Model(BaseModel):
        user_name: str

    field_info = Model.model_fields["user_name"]
    field_path = FieldPath(("user_name",))
    label = generate_label(field_path, field_info)
    assert label == "User Name"


def test_generate_label_uses_leaf_name_for_nested() -> None:
    class Inner(BaseModel):
        street_address: str

    class Outer(BaseModel):
        address: Inner

    field_info = Inner.model_fields["street_address"]
    field_path = FieldPath(("address", "street_address"))
    label = generate_label(field_path, field_info)
    assert label == "Street Address"


# --- UI Element Generation Tests ---


def test_generate_ui_for_int() -> None:
    class Model(BaseModel):
        age: int = Field(ge=0, le=120)

    field_info = Model.model_fields["age"]
    field_path = FieldPath(("age",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.number)


def test_generate_ui_for_float() -> None:
    class Model(BaseModel):
        ratio: float = Field(ge=0.0, le=1.0)

    field_info = Model.model_fields["ratio"]
    field_path = FieldPath(("ratio",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.number)


def test_generate_ui_for_str() -> None:
    class Model(BaseModel):
        name: str = Field(max_length=100)

    field_info = Model.model_fields["name"]
    field_path = FieldPath(("name",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.text)


def test_generate_ui_for_bool() -> None:
    class Model(BaseModel):
        is_active: bool = True

    field_info = Model.model_fields["is_active"]
    field_path = FieldPath(("is_active",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.checkbox)


def test_generate_ui_for_literal() -> None:
    class Model(BaseModel):
        status: Literal["pending", "active", "completed"]

    field_info = Model.model_fields["status"]
    field_path = FieldPath(("status",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.dropdown)


def test_generate_ui_for_enum() -> None:
    class Status(Enum):
        PENDING = "pending"
        ACTIVE = "active"

    class Model(BaseModel):
        status: Status

    field_info = Model.model_fields["status"]
    field_path = FieldPath(("status",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.dropdown)


def test_generate_ui_for_date() -> None:
    class Model(BaseModel):
        birth_date: dt.date

    field_info = Model.model_fields["birth_date"]
    field_path = FieldPath(("birth_date",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.date)


def test_generate_ui_for_datetime() -> None:
    class Model(BaseModel):
        created_at: dt.datetime

    field_info = Model.model_fields["created_at"]
    field_path = FieldPath(("created_at",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.datetime)


def test_generate_ui_for_optional_int() -> None:
    class Model(BaseModel):
        age: int | None = None

    field_info = Model.model_fields["age"]
    field_path = FieldPath(("age",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.number)


def test_generate_ui_for_optional_literal() -> None:
    class Model(BaseModel):
        status: Literal["a", "b"] | None = None

    field_info = Model.model_fields["status"]
    field_path = FieldPath(("status",))
    ui = generate_ui_element(field_path, field_info)
    assert isinstance(ui, mo.ui.dropdown)


# --- Unsupported Type Tests ---


def test_unsupported_union_type() -> None:
    class Model(BaseModel):
        value: int | str

    field_info = Model.model_fields["value"]
    field_path = FieldPath(("value",))

    with pytest.raises(UnsupportedTypeError) as exc_info:
        generate_ui_element(field_path, field_info)

    assert exc_info.value.field_path == field_path
    assert "value" in str(exc_info.value)


def test_unsupported_list_type() -> None:
    class Model(BaseModel):
        items: list[str]

    field_info = Model.model_fields["items"]
    field_path = FieldPath(("items",))

    with pytest.raises(UnsupportedTypeError) as exc_info:
        generate_ui_element(field_path, field_info)

    assert exc_info.value.field_path == field_path


# --- Model Structure Tests ---


def test_iter_model_structure_flat() -> None:
    class Model(BaseModel):
        a: int
        b: str

    items = list(iter_model_structure(Model))
    assert len(items) == 2
    assert items[0][0] == "field"
    assert items[0][1].as_dotted == "a"
    assert items[1][0] == "field"
    assert items[1][1].as_dotted == "b"


def test_iter_model_structure_nested() -> None:
    class Inner(BaseModel):
        x: int

    class Outer(BaseModel):
        a: str
        inner: Inner

    items = list(iter_model_structure(Outer))
    assert len(items) == 4

    assert items[0][0] == "field"
    assert items[0][1].as_dotted == "a"

    assert items[1][0] == "nested_start"
    assert items[1][1] == "inner"

    assert items[2][0] == "field"
    assert items[2][1].as_dotted == "inner.x"

    assert items[3][0] == "nested_end"
    assert items[3][1] == "inner"


# --- Integration Tests ---


def test_auto_generate_simple_model() -> None:
    class Model(BaseModel):
        name: str
        age: int

    builder = PydanticFormBuilder(model=Model)
    form = builder.build()
    assert form is not None


def test_auto_generate_with_overrides() -> None:
    class Model(BaseModel):
        name: str
        bio: str

    builder = PydanticFormBuilder(
        model=Model,
        ui={
            "bio": mo.ui.text_area(label="Bio"),
        },
    )
    form = builder.build()
    assert form is not None


def test_auto_generate_disabled() -> None:
    class Model(BaseModel):
        name: str

    builder = PydanticFormBuilder(
        model=Model,
        ui={},
        auto_generate=False,
    )

    with pytest.raises(ValueError, match="No UI element provided"):
        builder.build()


def test_auto_generate_disabled_with_all_fields() -> None:
    class Model(BaseModel):
        name: str

    builder = PydanticFormBuilder(
        model=Model,
        ui={"name": mo.ui.text(label="Name")},
        auto_generate=False,
    )
    form = builder.build()
    assert form is not None


def test_auto_generate_nested_model() -> None:
    class Inner(BaseModel):
        value: int

    class Outer(BaseModel):
        name: str
        inner: Inner

    builder = PydanticFormBuilder(model=Outer)
    form = builder.build()
    assert form is not None


def test_auto_generate_raises_for_unsupported() -> None:
    class Model(BaseModel):
        items: list[str]

    builder = PydanticFormBuilder(model=Model)

    with pytest.raises(UnsupportedTypeError):
        builder.build()
