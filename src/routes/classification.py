import os
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, APITimeoutError, OpenAIError

from src.llm import *
import json

from datetime import datetime, timezone

load_dotenv() # loading environment variables

current_file = Path(__file__).resolve()
project_root = current_file.parents[2] # our project root

app = FastAPI()

PROMPT_VERSION = "classification-v1"
TIMEOUT_SECS = 30


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
    prompt = get_prompt()
    start_time = datetime.now()
    try:
        
        client = OpenAI(base_url=os.environ["LLM_BASE_URL"],
                        api_key=os.environ["LLM_API_KEY"],
                        timeout=TIMEOUT_SECS,
                        max_retries=2)
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
                    }],
                temperature=0.2
            )        
        
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    except APITimeoutError:
        raise HTTPException(status_code=504,
                            detail=f"Failed to get response from LLM within {TIMEOUT_SECS} seconds")
    except AuthenticationError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed with upstream provider: {str(e)}"
        )
    except OpenAIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream LLM provider error: {str(e)}"
                )

    output_message = res.choices[0].message.content
    usage = res.usage

    return output_message, usage, duration_ms

def log_llm_usage(model, input_tokens, output_tokens, duration_ms, needed_repair):
    usage_log = {
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "needed_repair": needed_repair
            }

    Path(project_root / "logs").mkdir(parents=True, exist_ok=True)
    # Writing usage logs to file
    with open(project_root / "logs/llm_usage.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(usage_log) + "\n")

def clean_markdown_fences(raw_text):
    """Removes ```json ... ``` code fences and returns
       (cleaned_text, needed_repair)."""
    text = raw_text.strip()
    needed_repair = False

    if text.startswith("```"):
        needed_repair = True

        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        else:
            text = text.lstrip("`")

    if text.endswith("```"):
        needed_repair = True
        text = text[:-3].strip()

    return text.strip(), needed_repair

def log_to_quarantine(message, output_message, error):

    Path(project_root / "logs").mkdir(parents=True, exist_ok=True)

    quarantine_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_text": message.text,
        "raw_llm_output": output_message,
        "error": error
    }
    
    with open(project_root / "logs/quarantine.jsonl", mode="a", encoding="utf-8") as f:
        f.write(json.dumps(quarantine_record) + "\n")

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
    if (os.getenv("LLM_ENABLED", "1").lower() == "0" or
        os.getenv("LLM_ENABLED", "1").lower() == "false"):
        raise HTTPException(
            status_code=503,
            detail="Service is unavailable"
        )

    if (os.getenv("LLM_STUB", "0").lower() == "1" or
        os.getenv("LLM_STUB", "0").lower() == "true"):
        print(message.model_dump_json())
        return {
            "category": "billing",
            "urgency": "low",
            "confidence": 0.8,
            "reason": "The message explicitly states refund problem."
        }

    # Sending request to LLM
    output_message, usage_1, duration_1 = send_request(message)
    output_message, needed_repair_1 = clean_markdown_fences(output_message)

    try:
        # Validating the output format
        validated_output = MessageOutput.model_validate_json(output_message)

        # Logging SUCCESS on call 1
        log_llm_usage(
            os.environ["LLM_MODEL"],
            usage_1.prompt_tokens,
            usage_1.completion_tokens,
            duration_1,
            needed_repair_1
        )
        return validated_output

    except Exception as e:
        # CALL 1 failed
        log_llm_usage(
            os.environ["LLM_MODEL"],
            usage_1.prompt_tokens,
            usage_1.completion_tokens,
            duration_1,
            False)

        updated_message_txt = (message.text + "\n"
                           + output_message + " "
                           + str(e) + "\n"
                           + """Your previous answer was rejected for this reason. Return only
                                corrected JSON matching the schema.""")
        updated_message = MessageInput(text=updated_message_txt)

        try:
            updated_output_message, usage_2, duration_2 = send_request(updated_message)
            updated_output_message, _ = clean_markdown_fences(updated_output_message)
            # print("It works")
            validated_output = MessageOutput.model_validate_json(updated_output_message)

            # SUCCESS ON CALL 2
            log_llm_usage(
                os.environ["LLM_MODEL"],
                usage_2.prompt_tokens,
                usage_2.completion_tokens,
                duration_2,
                True)

        except Exception as e:

            # BOTH CALLS FAILED
            log_llm_usage(
                os.environ["LLM_MODEL"],
                usage_2.prompt_tokens,
                usage_2.completion_tokens,
                duration_2,
                True)

            log_to_quarantine(message, updated_output_message, str(e)) # sending record to quarantine

            raise HTTPException(status_code=422,
                                detail="LLM output failure")

    return validated_output
    

