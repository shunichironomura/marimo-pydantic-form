from pydantic import BaseModel
from pydantic.fields import FieldInfo

from marimo_pydantic_form.pydantic_helper import flatten_model, iter_leaf_fields, unflatten_model


def test_iter_leaf_fields_no_fields() -> None:
    class EmptyModel(BaseModel):
        pass

    fields = list(iter_leaf_fields(EmptyModel))
    assert fields == []


def test_iter_leaf_fields_single() -> None:
    class SingleFieldModel(BaseModel):
        value: int

    fields = list(iter_leaf_fields(SingleFieldModel))
    assert len(fields) == 1
    path, field_info = fields[0]
    assert path == ("value",)
    assert isinstance(field_info, FieldInfo)
    assert field_info.annotation is int


def test_iter_leaf_fields_nested() -> None:
    class InnerModel(BaseModel):
        inner_value: float

    class NestedModel(BaseModel):
        outer_value: str
        inner: InnerModel

    fields = list(iter_leaf_fields(NestedModel))
    assert len(fields) == 2

    path1, field_info1 = fields[0]
    assert path1 == ("outer_value",)
    assert isinstance(field_info1, FieldInfo)
    assert field_info1.annotation is str

    path2, field_info2 = fields[1]
    assert path2 == ("inner", "inner_value")
    assert isinstance(field_info2, FieldInfo)
    assert field_info2.annotation is float


def test_flatten_model() -> None:
    class Inner(BaseModel):
        a: int
        b: str

    class Outer(BaseModel):
        x: float
        y: Inner

    obj = Outer(x=1.5, y=Inner(a=10, b="test"))
    flat = flatten_model(obj)
    assert flat == {
        ("x",): 1.5,
        ("y", "a"): 10,
        ("y", "b"): "test",
    }


def test_unflatten_model() -> None:
    class Inner(BaseModel):
        a: int
        b: str

    class Outer(BaseModel):
        x: float
        y: Inner

    flat = {
        ("x",): 1.5,
        ("y", "a"): 10,
        ("y", "b"): "test",
    }
    obj = unflatten_model(Outer, flat)
    assert isinstance(obj, Outer)
    assert obj.x == 1.5
    assert isinstance(obj.y, Inner)
    assert obj.y.a == 10
    assert obj.y.b == "test"
