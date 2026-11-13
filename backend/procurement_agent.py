from time import perf_counter

from query_generator import generate_query
from query_executor import execute_query
from answer_generator import generate_answer


def ask_procurement(question: str):
    """
    Complete AI Procurement Assistant workflow.

    1. Generate MongoDB query.
    2. Validate and execute query.
    3. Generate a readable answer.
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question cannot be empty.")

    print("\n1. Generating MongoDB query...")

    started = perf_counter()
    generated_query = generate_query(question)
    query_done = perf_counter()

    if not isinstance(generated_query, dict):
        raise ValueError("Gemini response must be an object.")

    if set(generated_query.keys()) != {"pipeline"}:
        raise ValueError("Unexpected Gemini response format.")

    pipeline = generated_query["pipeline"]

    if not isinstance(pipeline, list):
        raise ValueError("Generated pipeline must be a list.")

    print("Generated pipeline:", pipeline)

    print("\n2. Validating and executing MongoDB query...")

    # The executor validates the pipeline before running it.
    results = execute_query(pipeline)
    database_done = perf_counter()

    print(f"MongoDB returned {len(results)} results.")

    print("\n3. Generating AI answer...")

    answer = generate_answer(question, results, pipeline=pipeline)
    answer_done = perf_counter()
    timings_ms = {
        "query": round((query_done-started)*1000, 2),
        "database": round((database_done-query_done)*1000, 2),
        "answer": round((answer_done-database_done)*1000, 2),
        "total": round((answer_done-started)*1000, 2),
    }
    print("Request timings (ms):", timings_ms)

    print("\n4. Workflow completed!")

    return {
        "question": question,
        "answer": answer,
        "results": results,
        "timings_ms": timings_ms,
    }


if __name__ == "__main__":

    question = "Who are the top 5 suppliers by total spending?"

    print("Question:", question)

    try:
        response = ask_procurement(question)

        print("\n" + "=" * 60)
        print("FINAL AI ANSWER")
        print("=" * 60)

        print(response["answer"])

    except Exception as error:
        print("\nERROR:", error)