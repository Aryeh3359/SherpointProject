# Serverless RAG Document Indexer & Retrieval Service

An enterprise-ready Retrieval-Augmented Generation (RAG) backend engineered to index documents from a repository (e.g., SharePoint) and serve grounded natural language answers with explicit source citations.

---

## 1. Architecture Overview

[Document Source / SharePoint Mock]
│
▼ (HTTP Ingestion / Blob Storage)
┌───────────────────────────┐
│    Azure Function App     │
│  (Python 3.11 Serverless) │
└────────────┬──────────────┘
│ Chunk & Index
▼
┌───────────────────────────┐
│    Search Index Store     │
│ (Azure AI Search / Local) │
└────────────┬──────────────┘
▲
│ Vector & Keyword Retrieval
┌────────────┴──────────────┐
│    RAG Query Endpoint     │
│        (/api/query)       │
└───────────────────────────┘
▲
│ Question Payload
[Client / User UI]


### Key Components
- **Serverless Compute:** Azure Functions (Python 3.11, Consumption Plan) hosting backend API endpoints.
- **Storage Tier:** Azure Blob Storage representing the SharePoint document repository.
- **Search & Vector Tier:** Azure AI Search with local in-memory fallback for offline testing[cite: 1].
- **Frontend Interface:** Streamlit chat application (`app.py`) for visual user interaction[cite: 1].
- **Infrastructure as Code (IaC):** Defined declaratively using Azure Bicep (`infra/main.bicep`)[cite: 1].
- **CI/CD Automation:** GitHub Actions (`.github/workflows/deploy.yml`) executing automated dependency validation and Bicep compilation on push[cite: 1].

---

## 2. API Endpoints

### 1. Ingest Document
* **Route:** `POST /api/index_document`
* **Payload:**
```json
{
  "doc_id": "sp_policy_001",
  "title": "Corporate Data Retention Policy",
  "content": "All corporate records must be retained for 7 years in secure cloud storage. After 7 years, documents can be archived or purged following compliance review."
}
Response:

JSON


{
  "message": "Document indexed successfully.",
  "doc_id": "sp_policy_001",
  "chunks_count": 1,
  "chunk_ids": ["sp_policy_001_chunk_0"]
}
2. Query Knowledge Base
Route: POST /api/query

Payload:

JSON


{
  "question": "How long do corporate records need to be kept?"
}
Response:

JSON


{
  "question": "How long do corporate records need to be kept?",
  "answer": "Based on Corporate Data Retention Policy:\nAll corporate records must be retained for 7 years...",
  "citations": [
    {
      "source": "Corporate Data Retention Policy",
      "chunk_id": "sp_policy_001_chunk_0"
    }
  ]
}
3. Local Development & Testing
Prerequisites
Python 3.10+

Azure Functions Core Tools (npm install -g azure-functions-core-tools@4)

Streamlit

Setup & Execution
Bash


# Clone the repository
git clone [https://github.com/Aryeh3359/SherpointProject.git](https://github.com/Aryeh3359/SherpointProject.git)
cd SherpointProject

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start the backend function host (in terminal 1)
func start --port 7072

# Launch the Streamlit frontend UI (in terminal 2)
streamlit run app.py
4. Architectural Decisions & Limitations
Refer to LIMITATIONS.md for details regarding:

SharePoint mocking using Azure Blob Storage interface abstractions.

Handling of cloud provider subscription quota limits during CI/CD validation through isolated template compilation[cite: 1].