from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

models = client.models.list()

# for m in models.data:
#     if "llama" in m.id.lower():
#         print(m.id)
def is_model_alive(model_name):
    try:
        client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1
        )
        return True
    except Exception as e:
        print(e)
        return False

print(is_model_alive("meta-llama/llama-3.3-70b-instruct:free"))
