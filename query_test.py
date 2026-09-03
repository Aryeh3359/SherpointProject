import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from google import genai

# 1. Load credentials from local.settings.json
with open("local.settings.json") as f:
    env = json.load(f)["Values"]

# 2. Initialize Azure AI Search
search_client = SearchClient(
    endpoint=env["SEARCH_ENDPOINT"], 
    index_name=env["SEARCH_INDEX_NAME"], 
    credential=AzureKeyCredential(env["SEARCH_KEY"])
)

# 3. Initialize the new Gemini client
client = genai.Client(api_key=env["GEMINI_API_KEY"])

# 4. Retrieve Context from Azure AI Search
question = "What are the core requirements of this task?"
print(f"Retrieving documents for: '{question}'...\n")

results = search_client.search(search_text=question, select=["content"], top=3)
context_chunks = [doc['content'] for doc in results]
context_string = "\n---\n".join(context_chunks)

# 5. Generate the Answer using gemini-2.5-flash
prompt = f"""You are an assistant analyzing task requirements. Answer the user's question using strictly the provided context below. 
Respond in the same language the question is asked in. If the context does not contain the answer, state that clearly.

Context:
{context_string}

Question:
{question}
"""

print("Synthesizing final answer...\n")
response = client.models.generate_content(
model="gemini-3.5-flash",
contents=prompt,
)

print("=== FINAL RAG OUTPUT ===")
print(response.text)