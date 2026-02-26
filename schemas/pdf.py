#schemas/ pdf.py
from pydantic import BaseModel

class PDFUploadResponse(BaseModel):
    thread_id : str
    filename : str
    documents : int  #number of pdf pages loaded
    chunks : int # numbers of chunks after splitting
    message : str


