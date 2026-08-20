"""One-time real OpenRouter integration test."""
import httpx
import json

BASE = "http://127.0.0.1:8000"

# Query that requires synthesis (can't be answered by deterministic extraction alone)
print("=== REAL OPENROUTER INTEGRATION TEST ===")
print()

r = httpx.post(
    f"{BASE}/queries/answer",
    json={"query": "Explain how the total amount is calculated in this document"}
)
data = r.json()

print(f"Status: {r.status_code}")
print()
print(f"Query: {data['query']}")
print(f"Answer: {data['answer']}")
print(f"Method: {data['method']}")
print(f"LLM used: {data['llm_used']}")
print(f"Confidence: {data['confidence']}")
print(f"Cache hit: {data['cache_hit']}")
print(f"Evidence: {len(data['evidence'])} items")
for i, e in enumerate(data['evidence'][:5]):
    src = e.get('source_type', '?')
    fld = e.get('field', '')
    val = e.get('value', e.get('text', ''))
    if isinstance(val, str) and len(val) > 60:
        val = val[:60] + '...'
    print(f"  {i+1}. [{src}] {fld}: {val}")

print()
usage = data['usage']
print("Usage:")
print(f"  prompt_tokens: {usage['prompt_tokens']}")
print(f"  completion_tokens: {usage['completion_tokens']}")
print(f"  total_tokens: {usage['total_tokens']}")
print(f"  estimated_cost: {usage['estimated_cost']}")
print(f"  retrieval_cost: {usage['retrieval_cost']}")

print()
print("=== INTEGRATION TEST COMPLETE ===")