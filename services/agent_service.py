# services/agent_service.py  [PHASE 3 — adds persistence]

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages

from core.config import settings
from core.database import checkpointer   # ← NEW: import checkpointer


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class AgentService:

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
        )
        self._graph = self._build_graph()

    def _build_graph(self):

        def chat_node(state: ChatState, config=None):
            system = SystemMessage(content="You are a helpful AI assistant.")
            response = self._llm.invoke([system, *state["messages"]])
            return {"messages": [response]}

        graph = StateGraph(ChatState)
        graph.add_node("chat_node", chat_node)
        graph.add_edge(START, "chat_node")

        # ← NEW: passing checkpointer enables persistent memory
        # LangGraph will save state to SQLite after every node execution
        return graph.compile(checkpointer=checkpointer)

    def invoke(self, message: str, thread_id: str) -> str:
        # ← NEW: the config dict is the key to memory.
        # LangGraph uses thread_id to find and load the right conversation
        # from SQLite before running the graph.
        config = {"configurable": {"thread_id": thread_id}}

        result = self._graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,       # ← pass config here
        )
        return result["messages"][-1].content

    def get_all_threads(self) -> list[str]:
        """List all thread IDs that have saved checkpoints."""
        threads = set()
        for checkpoint in checkpointer.list(None):
            threads.add(checkpoint.config["configurable"]["thread_id"])
        return list(threads)


agent_service = AgentService()