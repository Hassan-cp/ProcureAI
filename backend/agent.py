import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict


# 1. Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is missing!")


# 2. Initialize Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    google_api_key=api_key,
    temperature=0,
)


# 3. Define Agent State
class AgentState(TypedDict):
    question: str
    answer: str


# 4. Define Agent Node
def ask_gemini(state: AgentState):
    response = llm.invoke(state["question"])

    return {
        "answer": response.text
    }


# 5. Build LangGraph
workflow = StateGraph(AgentState)

workflow.add_node("ask_gemini", ask_gemini)

workflow.add_edge(START, "ask_gemini")
workflow.add_edge("ask_gemini", END)

agent = workflow.compile()


# 6. Test Agent
if __name__ == "__main__":
    result = agent.invoke({
        "question": "What is procurement?",
        "answer": "",
    })

    print("Agent Answer:")
    print(result["answer"])
    