# services/agent_service.py  [PHASE 2 — minimal version]
# In this phase: just an LLM call. No tools, no memory.
# We will add to this file in phases 3, 4, and 5.

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages

from core.config import settings


class ChatState(TypedDict):
    # add_messages reducer: new messages are APPENDED to the list, never replace it.
    # This is what gives LangGraph its memory within a single run.
    messages: Annotated[list[BaseMessage], add_messages]


class AgentService:

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
        )
        self._graph = self._build_graph()

    def _build_graph(self):
        """
        Minimal graph — just one node that calls the LLM.
        No tools, no checkpointer, no loops.

        Flow:  START → chat_node → END
        """

        def chat_node(state: ChatState, config=None):
            system = SystemMessage(content="You are a helpful AI assistant.")
            response = self._llm.invoke([system, *state["messages"]])
            return {"messages": [response]}

        graph = StateGraph(ChatState)
        graph.add_node("chat_node", chat_node)
        graph.add_edge(START, "chat_node")

        # No checkpointer in Phase 2 — no memory between requests
        return graph.compile()

    def invoke(self, message: str, thread_id: str) -> str:
        result = self._graph.invoke(
            {"messages": [HumanMessage(content=message)]}
        )
        return result["messages"][-1].content


# Singleton — created once, shared by all requests
agent_service = AgentService()