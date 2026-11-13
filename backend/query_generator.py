import json
import re
from difflib import SequenceMatcher
from datetime import datetime, timezone

from agent import llm
from fast_queries import common_query
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

def simple_latest_query(question):
    """Own unqualified latest-date intent; never discard user filters.

    Full matching is deliberate: bounded, departmental, fiscal and other
    qualified questions must keep their constraints in model generation.
    The executor supplies the live clock at execution, before aggregation.
    """
    text = re.sub(r"[?,.!]", " ", question.lower())
    text = " ".join(text.split())
    pattern = (
        r"(?:what is |what was |show me |give me )?(?:the )?"
        r"(?:most recent|latest|last) purchase (date|year)"
        r"(?: excluding future dates| without future dates)?"
    )
    match = re.fullmatch(pattern, text)
    if not match:
        return None
    year = match.group(1) == "year"
    return {"pipeline": [{"$group": {
        "_id": None,
        "latestYear" if year else "latestDate": {
            "$max": {"$year": "$Purchase Date"} if year else "$Purchase Date"
        },
    }}]}


def generate_query(question: str):
    direct = simple_latest_query(question) or common_query(question)
    if direct is not None:
        return direct
    current_time = datetime.now(timezone.utc).isoformat()


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

Current system UTC time: {current_time}
Use this system clock for relative dates; never guess today's date.
For latest purchase dates/years, do not add a cutoff unless the user
explicitly specifies a date bound. The executor applies the current clock.
Preserve all explicit user date bounds and other filters.

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
9. When the user asks about purchases in a specific year,
   month, or date range, ALWAYS filter using "Purchase Date",
   NOT "Fiscal Year", unless the user explicitly asks about
   fiscal years.

10. "Purchase Date" is stored as a MongoDB Date, not a string.
    Generate date comparisons using MongoDB Extended JSON:
    {{"$date": "2020-01-01T00:00:00Z"}}.
    Use $gte for the start date and $lt for the exclusive
    end date.

11. For example, "How many purchases were made in 2020?"
    means purchases with "Purchase Date" from
    2020-01-01 (inclusive) to 2021-01-01 (exclusive).

12. Supported stages: $match, $group, $sort, $limit, $project, $count.
    Never use $where, $function, $out, $merge, $lookup or $expr.
    For the latest purchase year use $group with
    {{"_id": null, "latestYear": {{"$max": {{"$year": "$Purchase Date"}}}}}}.
    The executor excludes invalid and future purchase dates automatically
    for latest-date queries. Do not replace Purchase Date with Fiscal Year.

Calendar quarters use Purchase Date in UTC. Unless explicitly aggregated across
all years, group by BOTH year and quarter. MongoDB has no $quarter operator;
use {{"$ceil": {{"$divide": [{{"$month": "$Purchase Date"}}, 3]}}}}.
Exclude null/non-date Purchase Date before date expressions. Frequency of line
items means record count per exact Item Name, not sum of Quantity; state this.

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
