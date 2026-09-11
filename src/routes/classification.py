import os
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dotenv import load_dotenv
from openai import OpenAI

from src.llm import *
import json

from datetime import datetime, timezone

load_dotenv() # loading environment variables

current_file = Path(__file__).resolve()
project_root = current_file.parents[2] # our project root

app = FastAPI()

def get_prompt():
    """
    Getting prompt from a file to send to AI
    """
    with open(r"C:\Users\User\OneDrive\Desktop\llm_integration\prompts\classification-v1.md",
              "r",
              encoding="utf-8") as file:
        return file.read()

def send_request(message):
    """
    Sending user message to AI
    """
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
                "content": message.model_dump_json()
            }
            ],
        temperature=0.2
    )
    output_message = res.choices[0].message.content
    return output_message

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

    # Sending request to LLM
    output_message = send_request(message)
    
    if (output_message.startswith("```json") or
        output_message.endswith("```")):
        output_message = output_message.strip("`json")
    try:
        validated_output = MessageOutput.model_validate_json(output_message)
    except Exception as e:
        updated_message_txt = (message.text + "\n"
                           + output_message + " "
                           + str(e) + "\n"
                           + """Your previous answer was rejected for this reason. Return only
                                corrected JSON matching the schema.""")
        updated_message = MessageInput(text=updated_message_txt)
        try:
            updated_output_message = send_request(updated_message)
            print("It works")
            validated_output = MessageOutput.model_validate_json(updated_output_message)
        except Exception as e:
            Path(project_root / "logs").mkdir(parents=True, exist_ok=True)

            quarantine_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_text": message.text,
                "raw_llm_output": updated_output_message,
                "error": str(e)
            }

            with open(project_root / "logs/quarantine.jsonl", mode="a", encoding="utf-8") as f:
                # json.dump(output_message + str(e) + message.text, f, indent=4)
                f.write(json.dumps(quarantine_record) + "\n")

            raise HTTPException(status_code=422,
                                detail="LLM output failure")

    return validated_output
    

