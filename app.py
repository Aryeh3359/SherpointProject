import streamlit as st
import requests
import os

st.set_page_config(
    page_title="Azure RAG & Gemini Agent",
    page_icon="✨",
    layout="centered"
)

# Custom Sleek Styling with a Computer/Digital Library Background & Animated Brain
st.markdown("""
<style>
    .stApp {
        background-image: linear-gradient(rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.88)), 
                          url("https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&q=80&w=1920");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    .stChatMessage {
        padding: 1.2rem;
        border-radius: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
        border: 1px solid #edf2f7;
        background-color: rgba(255, 255, 255, 0.92);
    }

    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.95);
        border-right: 1px solid #e2e8f0;
        padding: 2rem 1rem;
    }

    h1 {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-weight: 700;
        color: #1a202c;
        letter-spacing: -0.025em;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.15); }
        100% { transform: scale(1); }
    }
    
    .animated-brain {
        display: inline-block;
        animation: pulse 2s infinite ease-in-out;
    }
    
    .stButton button {
        border-radius: 0.50rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# Main Title with the animated brain icon
st.markdown("# <span class='animated-brain'>🧠</span> Azure RAG & Gemini Agent", unsafe_allow_html=True)
st.markdown("<p style='color: #2d3748; font-size: 1.1rem; margin-bottom: 2rem; font-weight: 500;'>Your intelligent workspace for document search, multi-turn analysis, and automated file management.</p>", unsafe_allow_html=True)

# Sidebar for configuration and file management
with st.sidebar:
    st.markdown("### ⚙️ System Settings")
    chat_endpoint = st.text_input(
        "Backend Chat URL", 
        value="https://rag-indexer-app-ari.azurewebsites.net/api/chat"
    )
    
    # Deriving base URL automatically from the chat endpoint input
    base_backend_url = chat_endpoint.rsplit('/api/', 1)[0]
    
    st.divider()
    st.markdown("### 📚 Active Knowledge Base")
    if st.button("Refresh File List", use_container_width=True):
        with st.spinner("Fetching files..."):
            try:
                response = requests.get(f"{base_backend_url}/api/list_files", timeout=10)
                if response.status_code == 200:
                    files = response.json().get("files", [])
                    if files:
                        for file in files:
                            st.write(f"📄 **{file}**")
                    else:
                        st.info("No files currently indexed.")
                else:
                    st.error("Failed to fetch file list.")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")
                
    st.divider()
    st.markdown("### 📂 Upload Document")
    uploaded_file = st.file_uploader("Upload Document (PDF / TXT)", type=["pdf", "txt"])
    
    if uploaded_file is not None:
        os.makedirs("uploads", exist_ok=True)
        local_path = os.path.abspath(os.path.join("uploads", uploaded_file.name))
        
        with open(local_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        st.info(f"File staged: `{uploaded_file.name}`")
        
        if st.button("🚀 Index to Azure Search", use_container_width=True):
            with st.spinner("Processing & Indexing..."):
                payload = {
                    "question": f"Please add a file named {uploaded_file.name} using the file on my computer at {local_path}"
                }
                try:
                    response = requests.post(chat_endpoint, json=payload, timeout=120)
                    if response.status_code == 200:
                        st.success("Successfully indexed!")
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Ask a question about your documents or request file actions..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    chat_endpoint, 
                    json={"question": prompt}, 
                    timeout=60
                )
                
                if response.status_code == 200:
                    answer = response.json().get("answer", "No response content returned.")
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    error_msg = f"[Error {response.status_code}]: {response.text}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    
            except Exception as e:
                error_msg = f"Failed to connect to backend: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})