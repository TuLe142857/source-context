from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def index():  # type: ignore
    return {"Hello": "World"}
