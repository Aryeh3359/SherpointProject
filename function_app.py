import azure.functions as func
import json
import logging
import re

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

LOCAL_DOCUMENT_INDEX = []

def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += (chunk_size - chunk_overlap)
    return chunks

@app.route(route="index_document", methods=["POST"])
def index_document(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing index_document request.")
    try:
        req_body = req.get_json()
        doc_id = req_body.get("doc_id")
        title = req_body.get("title", "Untitled")
        content = req_body.get("content", "")

        if not doc_id or not content:
            return func.HttpResponse(
                json.dumps({"error": "'doc_id' and 'content' are required fields."}),
                status_code=400,
                mimetype="application/json"
            )

        global LOCAL_DOCUMENT_INDEX
        # Remove existing chunks for this doc_id if updating
        LOCAL_DOCUMENT_INDEX = [chunk for chunk in LOCAL_DOCUMENT_INDEX if chunk["doc_id"] != doc_id]

        chunks = chunk_text(content)
        indexed_chunks = []
        for idx, chunk in enumerate(chunks):
            record = {
                "chunk_id": f"{doc_id}_chunk_{idx}",
                "doc_id": doc_id,
                "title": title,
                "text": chunk
            }
            LOCAL_DOCUMENT_INDEX.append(record)
            indexed_chunks.append(record["chunk_id"])

        return func.HttpResponse(
            json.dumps({
                "message": "Document indexed/updated successfully.",
                "doc_id": doc_id,
                "chunks_count": len(chunks),
                "chunk_ids": indexed_chunks
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="delete_document", methods=["POST"])
def delete_document(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing delete_document request.")
    try:
        req_body = req.get_json()
        doc_id = req_body.get("doc_id")

        if not doc_id:
            return func.HttpResponse(
                json.dumps({"error": "Field 'doc_id' is required for deletion."}),
                status_code=400,
                mimetype="application/json"
            )

        global LOCAL_DOCUMENT_INDEX
        initial_count = len(LOCAL_DOCUMENT_INDEX)
        LOCAL_DOCUMENT_INDEX = [chunk for chunk in LOCAL_DOCUMENT_INDEX if chunk["doc_id"] != doc_id]
        deleted_count = initial_count - len(LOCAL_DOCUMENT_INDEX)

        if deleted_count == 0:
            return func.HttpResponse(
                json.dumps({"message": f"No document found with doc_id '{doc_id}'."}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps({
                "message": f"Document '{doc_id}' and its chunks purged successfully.",
                "chunks_removed": deleted_count
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="query", methods=["POST"])
def query(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing query request.")
    try:
        req_body = req.get_json()
        question = req_body.get("question", "").strip()

        if not question:
            return func.HttpResponse(
                json.dumps({"error": "Field 'question' is required."}),
                status_code=400,
                mimetype="application/json"
            )

        query_tokens = set(re.findall(r"\w+", question.lower()))
        scored = []
        for record in LOCAL_DOCUMENT_INDEX:
            record_tokens = set(re.findall(r"\w+", record["text"].lower()))
            overlap = len(query_tokens.intersection(record_tokens))
            if overlap > 0:
                scored.append((overlap, record))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_matches = [item[1] for item in scored[:3]]

        if not top_matches:
            return func.HttpResponse(
                json.dumps({
                    "question": question,
                    "answer": "No matching document context was found for this query.",
                    "citations": []
                }),
                status_code=200,
                mimetype="application/json"
            )

        context_blocks = "\n\n".join([f"[{m['title']} - {m['chunk_id']}]: {m['text']}" for m in top_matches])
        citations = [{"source": m["title"], "chunk_id": m["chunk_id"]} for m in top_matches]
        answer_summary = f"Based on {citations[0]['source']}:\n{top_matches[0]['text'][:250]}..."

        return func.HttpResponse(
            json.dumps({
                "question": question,
                "answer": answer_summary,
                "context_used": context_blocks,
                "citations": citations
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )