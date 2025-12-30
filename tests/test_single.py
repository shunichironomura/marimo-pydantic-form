from pydantic import BaseModel

from marimo_pydantic_form import PydanticFormBuilder


def test_slider() -> None:
    class SingleValue(BaseModel):
        value: float

    form = PydanticFormBuilder(model=SingleValue)
        .build()
