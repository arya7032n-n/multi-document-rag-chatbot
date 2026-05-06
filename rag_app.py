import streamlit as st
from PyPDF2 import PdfReader

from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

st.set_page_config(page_title="AI Chatbot", layout="wide")

st.title("🤖 AI Multi-Document Chatbot")

# ---------------- LOAD MODEL ----------------
@st.cache_resource
def load_model():
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
    model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")
    return tokenizer, model

tokenizer, model = load_model()

# ---------------- PROCESS MULTIPLE PDFs ----------------
@st.cache_resource
def process_pdfs(pdf_files):
    all_text = ""

    for pdf in pdf_files:
        reader = PdfReader(pdf)
        for page in reader.pages:
            if page.extract_text():
                all_text += page.extract_text()

    splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=500,
        chunk_overlap=100
    )

    chunks = splitter.split_text(all_text)

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vectorstore = FAISS.from_texts(chunks, embeddings)

    return vectorstore

# ---------------- SESSION ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- SIDEBAR ----------------
st.sidebar.header("📂 Upload Documents")

pdf_files = st.sidebar.file_uploader(
    "Upload PDFs",
    type="pdf",
    accept_multiple_files=True
)

# Clear chat
if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages = []

# Clean file display
if pdf_files:
    st.sidebar.success(f"✅ Loaded {len(pdf_files)} file(s)")
    for file in pdf_files:
        st.sidebar.markdown(f"📄 **{file.name}**")

    st.sidebar.markdown("---")
    st.sidebar.info("🤖 Ready to answer from your documents")

# ---------------- MAIN ----------------
if pdf_files:

    vectorstore = process_pdfs(pdf_files)

    st.success("📚 Documents processed. Start chatting below!")

    # Show chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    query = st.chat_input("Ask something about your documents...")

    if query:
        st.session_state.messages.append({"role": "user", "content": query})

        with st.chat_message("user"):
            st.write(query)

        q = query.lower().strip()

        # ---------------- INTENT HANDLING ----------------

        if q in ["hi", "hello", "hey"]:
            response = "👋 Hey! I'm here to help. Ask me anything from your documents."

        elif any(word in q for word in ["shutup", "stupid", "idiot"]):
            response = "😅 Let's keep it friendly. Ask me something from your documents."

        elif q in ["who am i", "who is me"]:
            response = "🙂 I don’t know personal info. I only answer from your documents."

        elif "why can't" in q or "why cant" in q:
            response = "I only answer from your uploaded documents. If it's not there, I can't provide it."

        elif "summary" in q or "summarize" in q:
            docs = vectorstore.similarity_search(query, k=5)
            context = "\n\n".join([doc.page_content for doc in docs])

            prompt = f"Summarize the following:\n\n{context}"

            inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
            outputs = model.generate(**inputs, max_new_tokens=150)

            response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        elif q == "exit":
            response = "🛑 Session ended. Refresh the page to restart."

        elif len(q) < 4:
            response = "🙂 Try asking something like 'What is churn?' or 'Summarize the document.'"

        else:
            with st.spinner("🤔 Thinking..."):
                docs = vectorstore.similarity_search(query, k=3)

                context = "\n\n".join([doc.page_content for doc in docs])

                prompt = f"""
You are a professional AI assistant.

Rules:
- Answer ONLY from context
- If not found, say: "I cannot find this information in the documents."
- Keep answer clear and concise

Context:
{context}

Question:
{query}

Answer:
"""

                inputs = tokenizer(prompt, return_tensors="pt", truncation=True)

                outputs = model.generate(
                    **inputs,
                    max_new_tokens=100,
                    temperature=0.3
                )

                response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        st.session_state.messages.append({"role": "assistant", "content": response})

        with st.chat_message("assistant"):
            st.write(response)

else:
    st.info("👈 Upload one or more PDFs to begin")