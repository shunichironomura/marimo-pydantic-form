import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")

with app.setup:
    import marimo as mo
    from marimo_pydantic_form import PydanticFormBuilder
    from pydantic import BaseModel


@app.cell
def _():
    class Inner(BaseModel):
        a: int


    class Model(BaseModel):
        x: float
        y: Inner
    return (Model,)


@app.cell
def _(Model):
    builder = PydanticFormBuilder(
        model=Model, ui={"x": mo.ui.slider(0, 100, label="x"), "y.a": mo.ui.slider(0, 100, label="y.a")}
    )
    return (builder,)


@app.cell
def _(builder):
    form = builder.build()
    form
    return (form,)


@app.cell
def _(builder, form):
    builder.parse(form.value)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
