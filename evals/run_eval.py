import json
import httpx

# Reading the test cases from file
with open("evals/cases.json", "r", encoding="utf-8") as f:
    data = json.load(f)

num_evaluation_entries = len(data) # number of entries to test the LLM
success_count = 0  # to count successful responses based on evaluation set
failed_entries = [] # to keep failures in one place

for sample in data:
    # Sending request to live running server
    response = httpx.post(
        "http://127.0.0.1:8000/classification",
        json={"text": sample["input"]},
        timeout=None)
    result = response.json()
    # print(result)

    if (result["category"] == sample["expected"]["category"] and
        result["urgency"] == sample["expected"]["urgency"]):
        success_count += 1  # if our model returns right labels
    else:
        failed_entries.append(sample) # save failed entries

print(f"Our LLM became successful in {success_count} out of {num_evaluation_entries} entries")
print(f"Failed entries: {failed_entries}")