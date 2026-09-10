import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from openai import OpenAI
from src.llm import *

load_dotenv()

app = FastAPI()

def get_prompt():
    with open(r"C:\Users\User\OneDrive\Desktop\llm_integration\prompts\classification-v1.md",
              "r",
              encoding="utf-8") as file:
        return file.read()

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
    if os.getenv("LLM_STUB", "0") == "1":
        print(message.model_dump_json())
        return {
            "category": "billing",
            "urgency": "low",
            "confidence": 0.8,
            "reason": "The message explicitly states refund problem."
        }

    client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])

    res = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        messages=[
            {
                "role": "system",
                "content": get_prompt()
            },
            {
                "role": "user",
                "content": message.text
            }
            ],
        temperature=0.2
    )
    return res.choices[0].message.content
