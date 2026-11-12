import json
import re
from difflib import SequenceMatcher

from agent import llm
from query_executor import get_collection


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


# ============================================================
# DEPARTMENT NAME MATCHING
# ============================================================

_department_names_cache = None


def get_department_names():
    """
    Load actual department names from MongoDB.
    Cache them so we don't query MongoDB for every question.
    """
    global _department_names_cache

    if _department_names_cache is not None:
        return _department_names_cache

    client, collection = get_collection()

    try:
        names = collection.distinct("Department Name")

        _department_names_cache = sorted(
            name
            for name in names
            if isinstance(name, str) and name.strip()
        )

        return _department_names_cache

    finally:
        client.close()


def normalize_department_name(name):
    """
    Normalize department names so that:
    Department of Transportation
    Transportation, Department of

    become comparable.
    """
    name = name.lower().strip()

    name = re.sub(r"[^a-z0-9\s]", " ", name)

    words = name.split()

    # Remove common organizational words.
    stop_words = {
        "department",
        "of",
        "the",
    }

    words = [
        word
        for word in words
        if word not in stop_words
    ]

    return " ".join(sorted(words))


def find_department_matches(question, department_names):
    """
    Find department names relevant to the user's question.
    """

    normalized_question = normalize_department_name(question)

    matches = []

    for name in department_names:

        normalized_name = normalize_department_name(name)

        if not normalized_name:
            continue

        if normalized_name in normalized_question:
            matches.append((name, 1.0))
            continue

        similarity = SequenceMatcher(
            None,
            normalized_name,
            normalized_question
        ).ratio()

        if similarity >= 0.65:
            matches.append((name, similarity))

    matches.sort(
        key=lambda item: item[1],
        reverse=True
    )

    return [
        name
        for name, score in matches[:5]
    ]


# ============================================================
# QUERY GENERATION
# ============================================================

def generate_query(question: str):

    department_context = ""

    # Only look up department names for department-related questions.
    if "department" in question.lower():

        department_names = get_department_names()

        matches = find_department_matches(
            question,
            department_names
        )

        if matches:
            department_context = (
                "\nRelevant department names from the database:\n"
                + "\n".join(f"- {name}" for name in matches)
                + "\n\n"
                + "When filtering by department, use the exact "
                + "Department Name value from this list if it matches "
                + "the user's intended department.\n"
            )

    prompt = f"""
You are a MongoDB aggregation query generator.

Database schema:
{SCHEMA}

{department_context}

Rules:
1. Generate a MongoDB aggregation pipeline.
2. Use only fields from the provided schema.
3. Use read-only operations.
4. Return valid JSON only.
5. Do not include explanations or Markdown.
6. Use a maximum of 10 results unless the user requests fewer.
7. Do not invent fields.
8. When filtering by department, prefer the exact department
   name provided in the database context when applicable.

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

    question = (
        "How many purchases were made "
        "by the Department of Transportation?"
    )

    result = generate_query(question)

    print(json.dumps(result, indent=2))
