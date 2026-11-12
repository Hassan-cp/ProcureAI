import json

from agent import llm


SCHEMA = """
MongoDB collection: purchases

Available fields:
- Creation Date (date)
- Purchase Date (date or null)
- Fiscal Year (string)
- Purchase Order Number (string)
- Department Name (string)
- Supplier Name (string)
- Item Name (string)
- Item Description (string)
- Quantity (number)
- Unit Price (number or null)
- Total Price (number or null)
- Commodity Title (string)
- Classification Codes (string)
"""


def generate_query(question: str):
    prompt = f"""
You are a MongoDB aggregation query generator.

Database schema:
{SCHEMA}

Rules:
1. Generate a MongoDB aggregation pipeline.
2. Use only fields from the provided schema.
3. Use read-only operations.
4. Return valid JSON only.
5. Do not include explanations or Markdown.
6. Use a maximum of 10 results unless the user requests fewer.
7. Do not invent fields.


User question:
{question}

Return JSON in this format:
{{
    "pipeline": []
}}
"""

    response = llm.invoke(prompt)

    return json.loads(response.text)


if __name__ == "__main__":
    question = "Which 5 suppliers have the highest total spending?"

    result = generate_query(question)

    print(json.dumps(result, indent=2))