from typing import TypedDict

from anthropic import Anthropic
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    user_message: str
    response: str

client = Anthropic()

def ask_claude(state: State) -> dict:
    reply = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": state["user_message"]}],
    )
    return {"response": reply.content[0].text}

graph = StateGraph(State)
graph.add_node("ask_claude", ask_claude)
graph.add_edge(START, "ask_claude")
graph.add_edge("ask_claude", END)

app = graph.compile()
