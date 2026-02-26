# services/agent_service.py  [PHASE 5 — final version with RAG]

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from core.config import settings
from core.database import checkpointer
from services.rag_service import rag_service
from services.tools import calculator, get_stock_price, search_tool


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class AgentService:

    def __init__(self):
        self._llm = ChatOpenAI(model=settings.model_name, api_key=settings.openai_api_key)
        self._graph = self._build_graph()

    def _build_graph(self):
        # rag_tool is defined HERE so ToolNode knows about it at compile time,
        # but it resolves the retriever at CALL time using the thread_id argument.
        # This is the closure pattern: the function captures rag_service from scope,
        # then uses the runtime thread_id argument to find the right retriever.
        @tool
        def rag_tool(query: str, thread_id: str = "") -> dict:
            """
            Retrieve relevant passages from the PDF document uploaded for this thread.
            Always pass the current thread_id when calling this tool.
            Use this for any question about the content of an uploaded document.
            """
            retriever = rag_service.get_retriever(thread_id)
            if retriever is None:
                return {
                    "error": f"No PDF uploaded for thread '{thread_id}'. "
                             "Ask the user to upload a document first."
                }
            results = retriever.invoke(query)
            return {
                "query": query,
                "context": [doc.page_content for doc in results],
                "metadata": [doc.metadata for doc in results],
                "source_file": rag_service.get_metadata(thread_id).get("filename"),
            }

        # CRITICAL: rag_tool must be in BOTH bind_tools AND ToolNode
        # bind_tools → LLM knows it can call rag_tool
        # ToolNode   → graph can execute rag_tool when LLM calls it
        # A mismatch between these two lists = "Tool not found" crash at runtime
        all_tools = [search_tool, calculator, get_stock_price, rag_tool]
        llm_with_tools = self._llm.bind_tools(all_tools)
        tool_node = ToolNode(all_tools)

        def chat_node(state: ChatState, config=None):
            thread_id = config.get("configurable", {}).get("thread_id", "") if config else ""
            has_doc = rag_service.has_document(thread_id)

            doc_hint = (
                f"A PDF is available for thread '{thread_id}'. "
                "Use rag_tool with thread_id when the user asks about it."
                if has_doc else "No PDF uploaded for this thread yet."
            )

            system = SystemMessage(content=(
                "You are a helpful AI assistant.\n\n"
                f"Thread context: {doc_hint}\n\n"
                "Available tools:\n"
                f"  • rag_tool — answer questions about the uploaded PDF (thread_id='{thread_id}')\n"
                "  • search_tool — search the web\n"
                "  • calculator — arithmetic\n"
                "  • get_stock_price — live stock prices\n\n"
                "Always pass the thread_id argument when calling rag_tool."
            ))
            response = llm_with_tools.invoke([system, *state["messages"]], config=config)
            return {"messages": [response]}

        graph = StateGraph(ChatState)
        graph.add_node("chat_node", chat_node)
        graph.add_node("tools", tool_node)
        graph.add_edge(START, "chat_node")
        graph.add_conditional_edges("chat_node", tools_condition)
        graph.add_edge("tools", "chat_node")

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