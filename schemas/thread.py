# this service is used to display the threads on the threads endpoint.
# it shows the id number, if it has a document (RAG based) and its
# filename or chunks


#schemas/thread.py

from pydantic import BaseModel
from typing import Optional

class ThreadInfo(BaseModel):
    thread_id : str
    has_document : bool
    document_filename : Optional[str] = None
    document_chunks : Optional[int] = None
