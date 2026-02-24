# core/database.py
# The SQLite connection and LangGraph checkpointer live here as module-level singletons.
# One connection, shared across all requests.
#
# Why check_same_thread=False?
# SQLite's Python binding defaults to only allowing access from the thread that created
# the connection. FastAPI uses multiple threads. This flag disables that restriction.
# For production scale, use PostgreSQL with async SQLAlchemy instead of SQLite.

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from core.config import settings

# Created once when this module is first imported
_conn = sqlite3.connect(
    database=settings.sqlite_db_path,
    check_same_thread=False,
)

# checkpointer wraps the connection with LangGraph's save/load interface
checkpointer = SqliteSaver(conn=_conn)

def get_checkpointer() -> SqliteSaver:
    """
    Dependency injection factory.
    Currently returns the module singleton.
    If you swap to PostgreSQL later, only this function changes.
    """
    return checkpointer

