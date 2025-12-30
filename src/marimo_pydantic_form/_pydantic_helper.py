"""Helper functions for working with Pydantic models."""

from collections.abc import Generator
from dataclasses import dataclass
from inspect import isclass
from typing import ClassVar, Self

from pydantic import BaseModel
from pydantic.fields import FieldInfo


@dataclass(frozen=True, slots=True)
class FieldPath:
    """A path to a field in a Pydantic model."""

    parts: tuple[str, ...]

    SEPARATOR_NORMALIZED: ClassVar[str] = "__mpf__"  # mpf = marimo-pydantic-form

    @property
    def as_dotted(self) -> str:
        """Return the path as a dotted string."""
        return ".".join(self.parts)

    @classmethod
    def from_dotted(cls, dotted: str) -> Self:
        """Create a FieldPath from a dotted string."""
        parts = tuple(dotted.split("."))
        return cls(parts)

    @property
    def as_normalized(self) -> str:
        """Return the path as a string that can be used as an identifier."""
        return self.SEPARATOR_NORMALIZED.join(self.parts)

    @classmethod
    def from_normalized(cls, normalized: str) -> Self:
        """Create a FieldPath from a normalized string."""
        parts = tuple(normalized.split(cls.SEPARATOR_NORMALIZED))
        return cls(parts)


def iter_leaf_fields(model: type[BaseModel]) -> Generator[tuple[FieldPath, FieldInfo]]:
    """Iterate over all leaf fields of a Pydantic model, including nested models."""
    for field_name, field_info in model.model_fields.items():
        if (
            hasattr(field_info, "annotation")
            and isclass(field_info.annotation)
            and issubclass(field_info.annotation, BaseModel)
        ):
            # Nested Pydantic model
            nested_model = field_info.annotation
            for child_path, child_field_info in iter_leaf_fields(nested_model):
                yield (FieldPath((field_name, *child_path.parts)), child_field_info)
        else:
            yield (FieldPath((field_name,)), field_info)


def access_field(model: BaseModel, path: FieldPath) -> object:
    """Access a field of a Pydantic model given a path."""
    current_value: object = model
    for key in path.parts:
        if isinstance(current_value, BaseModel):
            current_value = getattr(current_value, key)  # pyright: ignore[reportAny]
        else:
            msg = f"Cannot access key '{key}' on non-BaseModel value '{current_value}'"
            raise TypeError(msg)
    return current_value


def flatten_model(model: BaseModel) -> dict[FieldPath, object]:
    """Flatten a Pydantic model into a dictionary of paths to values."""
    flat_dict: dict[FieldPath, object] = {}
    for path, _ in iter_leaf_fields(type(model)):
        flat_dict[path] = access_field(model, path)
    return flat_dict


def unflatten_model[T: BaseModel](model_cls: type[T], flat_dict: dict[FieldPath, object]) -> T:
    """Reconstruct a Pydantic model from a flattened dictionary of paths to values."""
    root_dict: dict[str, object] = {}
    for field_name, field_info in model_cls.model_fields.items():
        if (
            hasattr(field_info, "annotation")
            and isclass(field_info.annotation)
            and issubclass(field_info.annotation, BaseModel)
        ):
            # Nested Pydantic model
            nested_model_cls = field_info.annotation
            nested_flat_dict = {
                FieldPath(path.parts[1:]): value for path, value in flat_dict.items() if path.parts[0] == field_name
            }
            nested_model = unflatten_model(nested_model_cls, nested_flat_dict)
            root_dict[field_name] = nested_model
        elif FieldPath((field_name,)) in flat_dict:
            root_dict[field_name] = flat_dict[FieldPath((field_name,))]
        else:
            msg = f"Field '{field_name}' not found in flat_dict"
            raise KeyError(msg)
    return model_cls.model_validate(root_dict)
