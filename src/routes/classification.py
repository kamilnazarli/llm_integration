import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# from src.llm.schema import MessageInput, MessageOutput
from src.llm import *

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0]

    # 'loc' represents location path, e.g., ('body', 'text')
    # The last element is the name of the failing field
    loc = first_error.get("loc", [])
    field_name = loc[-1] if loc else "unknown"
    error_msg = first_error.get("msg", "Invalid value")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad Request",
            "field": str(field_name),
            "message": f"Validation failed for field '{field_name}': {error_msg}",
        },
    )

@app.get("/")
async def root():
    return { "name": "Task API", "version": "1.0", "endpoints": ["/classification"]}

@app.post("/classification")
async def classify(message: MessageInput):
    if int(os.getenv("LLM_STUB", 0)) == 1:
        return {
            "category": "billing",
            "urgency": "low",
            "confidence": 0.8,
            "reason": "The message explicitly states refund problem."
        }

# client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])

# res = client.chat.completions.create(
#     model=os.environ["LLM_MODEL"],
#     messages=[{"role": "user", "content": "Reply with exactly the word: ready"}],
# )