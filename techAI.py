import json

from openai import OpenAI
from config import log_techAI, SYSTEM_PROMPT, OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)


def gen_post(data):
    log_techAI.info("Generando post...")

    if not isinstance(data, (str, list)):
        data = json.dumps(data, ensure_ascii=False, indent=2)

    response = client.responses.create(
        model="gpt-4o",
        instructions=SYSTEM_PROMPT,
        input=data,
        tools=[{"type": "web_search"}],
    )

    return response.output_text