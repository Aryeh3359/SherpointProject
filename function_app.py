import azure.functions as func
import logging
import os
import json
import base64
import shutil
from PyPDF2 import PdfReader
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from google import genai

app = func.FunctionApp()

def chunk_text(text, chunk_size=1000, overlap=100):
    """Splits text into chunks of specified size with overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def index_file_to_search(file_path, filename):
    """Directly extracts text from a local file and indexes it into Azure AI Search."""
    search_endpoint = os.environ.get("SEARCH_ENDPOINT")
    search_key = os.environ.get("SEARCH_KEY")
    index_name = os.environ.get("SEARCH_INDEX_NAME")
    
    if not search_endpoint or not search_key or not index_name:
        logging.error("Search credentials missing in environment variables.")
        return False

    credential = AzureKeyCredential(search_key)
    search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
    
    # 1. Cleanup existing chunks for this file
    try:
        existing_docs = search_client.search(
            search_text="*", 
            filter=f"source_file eq '{filename}'", 
            select=["id"]
        )
        old_doc_ids = [{"id": doc["id"]} for doc in existing_docs]
        if old_doc_ids:
            search_client.delete_documents(documents=old_doc_ids)
            logging.info(f"Purged {len(old_doc_ids)} old chunks for existing file: {filename}")
    except Exception as cleanup_err:
        logging.warning(f"Could not purge old chunks: {str(cleanup_err)}")

    # 2. Extract text based on file type
    extracted_text = ""
    if filename.endswith(".pdf"):
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            extracted_text = f.read()

    if not extracted_text.strip():
        logging.warning(f"No text extracted from {filename}.")
        return False

    # 3. Chunk and upload
    text_chunks = chunk_text(extracted_text)
    search_documents = []
    for i, chunk in enumerate(text_chunks):
        raw_id = f"{filename}-{i}"
        safe_id = base64.urlsafe_b64encode(raw_id.encode()).decode().rstrip("=")
        search_documents.append({
            "id": safe_id,
            "source_file": filename,
            "content": chunk
        })
        
    search_client.upload_documents(documents=search_documents)
    logging.info(f"Successfully indexed {len(search_documents)} chunks for {filename}.")
    return True

# --- TOOL DEFINITIONS FOR AGENT JOB RUNNER ---
def manage_local_document_file(action: str, filename: str, content: str = "", source_path: str = "") -> str:
    """
    Manages local document files for the RAG system and indexes them into search.
    
    Args:
        action: The operation to perform, must be either 'add' or 'delete'.
        filename: The target filename in the documents folder (e.g., 'costemer_rights.pdf').
        content: Text content to write if creating a text file from scratch.
        source_path: Optional absolute or relative path to a file on your computer to upload/copy.
    """
    os.makedirs("documents", exist_ok=True)
    file_path = os.path.join("documents", filename)

    if action == "add":
        if source_path and os.path.exists(source_path):
            shutil.copy(source_path, file_path)
            success = index_file_to_search(file_path, filename)
            if success:
                return f"Successfully uploaded and indexed '{filename}' from '{source_path}'."
            return f"Copied '{filename}', but text extraction/indexing encountered an issue."
        elif content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            success = index_file_to_search(file_path, filename)
            if success:
                return f"Successfully created and indexed text file '{filename}'."
            return f"Created '{filename}', but indexing encountered an issue."
        return f"Error: Provide either a valid 'source_path' or 'content' to add {filename}."

    elif action == "delete":
        if os.path.exists(file_path):
            os.remove(file_path)
            
            search_endpoint = os.environ.get("SEARCH_ENDPOINT")
            search_key = os.environ.get("SEARCH_KEY")
            index_name = os.environ.get("SEARCH_INDEX_NAME")
            
            if search_endpoint and search_key and index_name:
                try:
                    credential = AzureKeyCredential(search_key)
                    search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
                    existing_docs = search_client.search(
                        search_text="*", 
                        filter=f"source_file eq '{filename}'", 
                        select=["id"]
                    )
                    old_doc_ids = [{"id": doc["id"]} for doc in existing_docs]
                    if old_doc_ids:
                        search_client.delete_documents(documents=old_doc_ids)
                        return f"Successfully deleted local file '{filename}' and purged {len(old_doc_ids)} chunks from Azure Search."
                except Exception as e:
                    return f"Deleted local file, but failed to purge from Azure Search: {str(e)}"
            return f"Successfully deleted local file '{filename}'."
        return f"File '{filename}' was not found in the documents directory."
    
    return f"Invalid action '{action}' specified."


@app.route(route="chat", auth_level=func.AuthLevel.ANONYMOUS)
def chat(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing RAG chat request with direct-indexing tool support.")
    
    try:
        req_body = req.get_json()
        question = req_body.get("question")
    except ValueError:
        question = req.params.get("question")

    if not question:
        return func.HttpResponse(
            json.dumps({"error": "Please pass a question in the request body or query string."}, ensure_ascii=False),
            status_code=400,
            mimetype="application/json"
        )

    try:
        search_client = SearchClient(
            endpoint=os.environ["SEARCH_ENDPOINT"], 
            index_name=os.environ["SEARCH_INDEX_NAME"], 
            credential=AzureKeyCredential(os.environ["SEARCH_KEY"])
        )
        
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        # Fetch relevant context from search for RAG queries
        results = search_client.search(
            search_text=question, 
            select=["content", "source_file"], 
            top=3
        )
        
        context_chunks = [f"[Source: {doc.get('source_file', 'unknown')}]\n{doc['content']}" for doc in results]
        context_string = "\n---\n".join(context_chunks) if context_chunks else "No relevant document context found."

        system_instruction = (
            "You are an intelligent RAG assistant. Answer the user's question accurately using the provided context. "
            "If the user asks to add, update, or delete a file, use the 'manage_local_document_file' tool."
        )

        prompt = f"""Context from knowledge base:
{context_string}

User Request:
{question}
"""

        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "tools": [manage_local_document_file],
                "temperature": 0.2
            }
        )
        
        answer_text = response.text if response.text else "Action completed successfully."

        return func.HttpResponse(
            json.dumps({"answer": answer_text}, ensure_ascii=False),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in chat endpoint: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="list_files", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def list_files(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Fetching list of indexed files.")
    try:
        search_client = SearchClient(
            endpoint=os.environ["SEARCH_ENDPOINT"], 
            index_name=os.environ["SEARCH_INDEX_NAME"], 
            credential=AzureKeyCredential(os.environ["SEARCH_KEY"])
        )
        
        results = search_client.search(search_text="*", select=["source_file"], top=1000)
        unique_files = list(set(doc.get("source_file") for doc in results if doc.get("source_file")))
        
        return func.HttpResponse(
            json.dumps({"files": unique_files}, ensure_ascii=False),
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error fetching files: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            status_code=500,
            mimetype="application/json"
        )