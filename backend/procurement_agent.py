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

    generated_query = generate_query(question)

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

    print(f"MongoDB returned {len(results)} results.")

    print("\n3. Generating AI answer...")

    answer = generate_answer(question, results)

    print("\n4. Workflow completed!")

    return {
        "question": question,
        "answer": answer,
        "results": results,
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