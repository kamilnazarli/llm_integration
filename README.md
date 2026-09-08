# LLM Integration


## Provider Configuration or Architecture
The API isolates the model provider behind three environment variables (LLM_API_KEYLLM_BASE_URL, LLM_MODEL). Provider details are never hardcoded: changing between an offline local model and a hosted datacenter endpoint requires altering only three environment variables.