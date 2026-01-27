# marimo-pydantic-form

> [!WARNING]
> This package is under active development. Features and APIs may change.

A Python package for building [marimo](https://marimo.io/) forms from [Pydantic](https://docs.pydantic.dev/) models.

## Features

- Automatically generate marimo forms from Pydantic models
- **Auto-generate UI elements** based on field types and Pydantic constraints
- Support for nested Pydantic models with hierarchical form layout
- Customizable UI elements for each field (override auto-generated defaults)
- Type-safe form validation using Pydantic
- Easy parsing of form values back into Pydantic model instances

## Installation

```bash
pip install marimo-pydantic-form
```

Or using uv:

```bash
uv add marimo-pydantic-form
```

## Quick Start

```python
import marimo as mo
from pydantic import BaseModel, Field
from marimo_pydantic_form import PydanticFormBuilder

class Address(BaseModel):
    street: str
    city: str

class Person(BaseModel):
    name: str = Field(max_length=100)
    age: int = Field(ge=0, le=120)
    is_active: bool = True
    address: Address

# UI elements are auto-generated based on field types
builder = PydanticFormBuilder(model=Person)

# Build the form
form = builder.build()

# Parse the form value into a Pydantic model instance
model_instance = builder.parse(form.value)
```

The form automatically generates appropriate UI elements:

- `str` fields → `mo.ui.text`
- `int`/`float` fields → `mo.ui.number` (with bounds from `ge`, `le`, `gt`, `lt` constraints)
- `bool` fields → `mo.ui.checkbox`
- `Literal` types → `mo.ui.dropdown`
- `Enum` types → `mo.ui.dropdown`
- `datetime.date` → `mo.ui.date`
- `datetime.datetime` → `mo.ui.datetime`

Nested models are displayed with hierarchical headers for visual clarity.

## Usage

### Basic Form (Auto-generation)

Create a form with automatically generated UI elements:

```python
from marimo_pydantic_form import PydanticFormBuilder

builder = PydanticFormBuilder(model=YourModel)
form = builder.build()
```

### Custom UI Elements (Overrides)

Override specific fields while auto-generating the rest:

```python
import marimo as mo
from pydantic import BaseModel
from marimo_pydantic_form import PydanticFormBuilder

class Model(BaseModel):
    name: str
    bio: str
    age: int

builder = PydanticFormBuilder(
    model=Model,
    ui={
        # Override 'bio' with a text area instead of text input
        "bio": mo.ui.text_area(label="Biography", placeholder="Tell us about yourself..."),
    },
)
form = builder.build()
```

### Nested Fields

Use dot notation for nested field paths:

```python
builder = PydanticFormBuilder(
    model=Model,
    ui={
        "address.city": mo.ui.dropdown(options=["New York", "Los Angeles", "Chicago"]),
    },
)
```

### Disable Auto-generation

To require manual UI specification for all fields (original behavior):

```python
builder = PydanticFormBuilder(
    model=Model,
    ui={
        "name": mo.ui.text(label="Name"),
        "age": mo.ui.number(label="Age"),
    },
    auto_generate=False,
)
```

### Parsing Form Values

Convert form values back to Pydantic model instances:

```python
model_instance = builder.parse(form.value)
```

## Supported Types

| Python Type | marimo UI Element | Notes |
|-------------|-------------------|-------|
| `int` | `mo.ui.number` | `step=1`, uses `ge`/`le`/`gt`/`lt` for bounds |
| `float` | `mo.ui.number` | Uses `ge`/`le`/`gt`/`lt` for bounds |
| `str` | `mo.ui.text` | Uses `max_length` constraint |
| `bool` | `mo.ui.checkbox` | |
| `Literal[...]` | `mo.ui.dropdown` | Options from literal values |
| `Enum` | `mo.ui.dropdown` | Options from enum members |
| `datetime.date` | `mo.ui.date` | |
| `datetime.datetime` | `mo.ui.datetime` | |
| `Optional[T]` | Unwraps to T | `allow_select_none=True` for dropdowns |

Unsupported types (e.g., `List`, `Union`) will raise `UnsupportedTypeError`. Provide a manual UI element for these fields.

## License

See [LICENSE](LICENSE) file for details.
