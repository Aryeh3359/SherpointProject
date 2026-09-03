import os
import requests
from PyPDF2 import PdfReader

# Path to your local file
file_path = r"C:\Users\a0533\Downloads\costemer_rights.pdf"
print(f"Reading local file: {file_path}")

if not os.path.exists(file_path):
    print(f"Error: File not found at {file_path}")
    exit(1)

# Extract text from the PDF
reader = PdfReader(file_path)
text = ""
for page in reader.pages:
    text += page.extract_text() or ""

print(f"Extracted {len(text)} characters. Sending to Azure backend...")

# Your backend endpoint (local or cloud)
# If testing locally use 'http://localhost:7071/api/chat' or your live Azure URL
backend_url = "https://rag-indexer-app-ari.azurewebsites.net/api/chat"

# Payload matching your backend's expected structure
payload = {
    "message": f"Please index this document titled costemer_rights.pdf with the following content:\n\n{text[:10000]}"
}

try:
    response = requests.post(backend_url, json=payload)
    if response.status_code == 200:
        print("Successfully sent document to Azure backend for indexing!")
        print("Response:", response.json().get("reply", "Indexed successfully."))
    else:
        print(f"Failed with status code {response.status_code}: {response.text}")
except Exception as e:
    print(f"Error connecting to backend: {str(e)}")