# services/agent_service.py  [PHASE 4 — adds tools and agent loop]

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition   # ← NEW

from core.config import settings
from core.database import checkpointer
from services.tools import calculator, get_stock_price, search_tool  # ← NEW


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class AgentService:

    def __init__(self):
        self._llm = ChatOpenAI(model=settings.model_name, api_key=settings.openai_api_key)
        self._graph = self._build_graph()

    def _build_graph(self):
        """
        Phase 4 graph — adds tools and conditional routing.

        tools_condition is a pre-built LangGraph function that checks the last message:
          - If it has tool_calls → route to "tools" node
          - If it has no tool_calls → route to END

        This creates the agent loop: LLM calls tool → tool runs → LLM sees result → LLM answers
        """
        base_tools = [search_tool, calculator, get_stock_price]

        # bind_tools tells the LLM what tools exist (sends schemas to OpenAI function-calling)
        llm_with_tools = self._llm.bind_tools(base_tools)

        # ToolNode is a pre-built node that executes whatever tool the LLM requested
        # It needs the EXACT same tool list as bind_tools — a mismatch = "Tool not found" crash
        tool_node = ToolNode(base_tools)

        def chat_node(state: ChatState, config=None):
            thread_id = config.get("configurable", {}).get("thread_id", "") if config else ""

            system = SystemMessage(content=(
                "You are a helpful AI assistant.\n"
                "Available tools:\n"
                "  • search_tool — search the web for current information\n"
                "  • calculator — perform arithmetic (add, sub, mul, div)\n"
                "  • get_stock_price — fetch live stock prices by ticker symbol\n"
            ))
            response = llm_with_tools.invoke([system, *state["messages"]], config=config)
            return {"messages": [response]}

        graph = StateGraph(ChatState)
        graph.add_node("chat_node", chat_node)
        graph.add_node("tools", tool_node)
        graph.add_edge(START, "chat_node")
        graph.add_conditional_edges("chat_node", tools_condition)  # ← branching
        graph.add_edge("tools", "chat_node")                       # ← the loop back

        return graph.compile(checkpointer=checkpointer)

    def invoke(self, message: str, thread_id: str) -> str:
        config = {"configurable": {"thread_id": thread_id}}
        result = self._graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        return result["messages"][-1].content

    def get_all_threads(self) -> list[str]:
        threads = set()
        for checkpoint in checkpointer.list(None):
            threads.add(checkpoint.config["configurable"]["thread_id"])
        return list(threads)


agent_service = AgentService()