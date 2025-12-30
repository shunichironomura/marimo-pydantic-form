# marimo-pydantic-form

> [!WARNING]
> This package is under active development. Features and APIs may change.

A Python package for building [marimo](https://marimo.io/) forms from [Pydantic](https://docs.pydantic.dev/) models.

> [!NOTE]
> Currently, UI elements must be manually assigned to each field. Automatic UI element generation is planned for future releases.

## Features

- Automatically generate marimo forms from Pydantic models
- Support for nested Pydantic models
- Customizable UI elements for each field
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
from pydantic import BaseModel
from marimo_pydantic_form import PydanticFormBuilder

class Inner(BaseModel):
    a: int

class Model(BaseModel):
    x: float
    y: Inner

# Create a form builder with custom UI elements
builder = PydanticFormBuilder(
    model=Model,
    ui={
        "x": mo.ui.slider(0, 100, label="x"),
        "y.a": mo.ui.slider(0, 100, label="y.a")
    },
)

# Build the form
form = builder.build()

# Parse the form value into a Pydantic model instance
model_instance = builder.parse(form.value)
```

## Usage

### Basic Form

Create a form from a Pydantic model:

```python
from marimo_pydantic_form import PydanticFormBuilder

builder = PydanticFormBuilder(model=YourModel)
form = builder.build()
```

### Custom UI Elements

Assign custom marimo UI elements to specific fields using dot notation for nested fields:

```python
builder = PydanticFormBuilder(
    model=Model,
    ui={
        "field_name": mo.ui.text(label="Custom Label"),
        "nested.field": mo.ui.slider(0, 100)
    }
)
```

### Parsing Form Values

Convert form values back to Pydantic model instances:

```python
model_instance = builder.parse(form.value)
```

## License

See [LICENSE](LICENSE) file for details.
