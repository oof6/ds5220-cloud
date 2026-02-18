import json
from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return detailed validation errors instead of generic 422."""
    return responses.JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "detail": "Request body could not be validated. Ensure Content-Type: application/json and the body is valid JSON (e.g. SNS subscription confirmation).",
            "validation_errors": exc.errors(),
        },
    )

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


# create a new endpoint that returns data POSTed to it 
# (e.g. SNS subscription confirmation)
@app.post("/data")
async def post_data(request: Request):
    try:
        body_bytes = await request.body()
    except Exception as e:
        return responses.JSONResponse(
            status_code=400,
            content={
                "error": "Bad request",
                "detail": "Could not read request body.",
                "message": str(e),
            },
        )

    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as e:
        return responses.JSONResponse(
            status_code=400,
            content={
                "error": "Invalid JSON",
                "detail": "Request body is not valid JSON.",
                "message": str(e),
                "position": {"line": e.lineno, "column": e.colno},
            },
        )

    print("Received SNS message. Payload contains:")
    print(data)
    return {"sns": "Received SNS message", "payload": data}

