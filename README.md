# LLM Integration


## Provider Configuration or Architecture
The API isolates the model provider behind three environment variables (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL). Provider details are never hardcoded: changing between an offline local model and a hosted datacenter endpoint requires altering only three environment variables.

## Endpoint test
Valid curl command:
```bash
curl.exe -X POST http://127.0.0.1:8000/classification -H "Content-Type: application/json" -d '{\"text\": \"The item arrived cracked and will not turn on.\"}'
```
Delibaretly broken curl:
```bash
curl.exe -X POST http://127.0.0.1:8000/classification -H "Content-Type: application/json" -d '{\"text\": \"\"}'
```