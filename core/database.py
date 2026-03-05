# core/database.py
# PostgreSQL connection and LangGraph checkpointer.
#
# Why psycopg.connect() instead of PostgresSaver.from_conn_string()?
# from_conn_string() returns a context manager (a generator) — it is designed
# for use inside a `with` block, not as a module-level singleton.
# Calling .setup() on the generator object (not the checkpointer) raises:
#   AttributeError: '_GeneratorContextManager' object has no attribute 'setup'
#
# psycopg.connect() gives a real connection object that PostgresSaver accepts directly.
#
# Why autocommit=True?
# LangGraph's PostgresSaver issues individual SQL statements and manages its own
# transaction boundaries internally. If autocommit is False (the default), psycopg3
# wraps everything in a transaction block — this conflicts with LangGraph's internal
# transaction management and causes errors. autocommit=True lets LangGraph control
# its own transactions.

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver

from core.config import settings

# Open one persistent connection at module level.
# autocommit=True is required by LangGraph's PostgresSaver.
_conn = psycopg.connect(settings.database_url, autocommit=True)

# Wrap the connection with LangGraph's save/load interface.
# setup() creates the checkpoints tables if they don't exist — safe to call every startup.
checkpointer = PostgresSaver(_conn)
checkpointer.setup()


def get_checkpointer() -> PostgresSaver:
    return checkpointer
