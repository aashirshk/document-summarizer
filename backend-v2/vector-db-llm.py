import os
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
import ollama
from types import SimpleNamespace
from pypdf import PdfReader
import logging

logging.getLogger("pypdf").setLevel(logging.ERROR)

# Load environment variables from .env file
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")  # unused now (left as-is to avoid other changes)

# === REPLACED: OpenAIEmbeddingFunction -> OllamaEmbeddingFunction ===
ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    model_name="nomic-embed-text",                     # pull first: `ollama pull nomic-embed-text`
    url="http://localhost:11434/api/embeddings",       # ensure `ollama serve` is running
)

# Initialize the Chroma client with persistence
chroma_client = chromadb.PersistentClient(path="./db/chroma_persistent_storage")
collection_name = "document_qa_collection"
collection = chroma_client.get_or_create_collection(
    name=collection_name, embedding_function=ollama_ef
)

# =================================
# === For initial setup -- Uncomment (below) all for the first run, and then comment it all out ===
# =================================
# Function to load documents from a directory
# def load_documents_from_directory(directory_path):
#     print("==== Loading documents from directory ====")
#     documents = []
#     for filename in os.listdir(directory_path):
#         if filename.endswith(".txt"):
#             with open(
#                 os.path.join(directory_path, filename), "r", encoding="utf-8"
#             ) as file:
#                 documents.append({"id": filename, "text": file.read()})
#     return documents

# REPLACE your load_documents_from_directory with this PDF version

def load_documents_from_directory(directory_path):
    print("==== Loading PDF documents from directory ====")
    documents = []
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(directory_path, filename)
            try:
                reader = PdfReader(pdf_path, strict=False)
                # extract text page by page
                pages_text = []
                for page in reader.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        pages_text.append(text)
                full_text = "\n".join(pages_text).strip()
                if full_text:
                    documents.append({"id": filename, "text": full_text})
                else:
                    print(f"!! Skipped (no extractable text): {filename}")
            except Exception as e:
                print(f"!! Error reading {filename}: {e}")
    return documents



# Function to split text into chunks
def split_text(text, chunk_size=1000, chunk_overlap=20):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - chunk_overlap
    return chunks


# Load documents from the directory
directory_path = "./pdfs"
documents = load_documents_from_directory(directory_path)


# Split the documents into chunks
chunked_documents = []
for doc in documents:
    chunks = split_text(doc["text"])
    print("==== Splitting docs into chunks ====")
    for i, chunk in enumerate(chunks):
        chunked_documents.append({"id": f"{doc['id']}_chunk{i+1}", "text": chunk})


# === REPLACED: OpenAI embeddings -> Ollama embeddings ===
def get_openai_embedding(text):
    # Using Ollama to generate embeddings (kept function name to avoid other changes)
    resp = ollama.embeddings(model="nomic-embed-text", prompt=text)
    embedding = resp["embedding"]
    print("==== Generating embeddings... ====")
    return embedding


# Generate embeddings for the document chunks
for doc in chunked_documents:
    print("==== Generating embeddings... ====")
    doc["embedding"] = get_openai_embedding(doc["text"])


# Upsert documents with embeddings into Chroma
for doc in chunked_documents:
    print("==== Inserting chunks into db;;; ====")
    collection.upsert(
        ids=[doc["id"]], documents=[doc["text"]], embeddings=[doc["embedding"]]
    )


# === End of the initial setup -- Uncomment all for the first run, and then comment it all out ===
# =================================


# Function to query documents
def query_documents(question, n_results=2):
    # query_embedding = get_openai_embedding(question)
    results = collection.query(query_texts=question, n_results=n_results)

    # Extract the relevant chunks
    relevant_chunks = [doc for sublist in results["documents"] for doc in sublist]
    print("==== Returning relevant chunks ====")
    return relevant_chunks
    # for idx, document in enumerate(results["documents"][0]):
    #     doc_id = results["ids"][0][idx]
    #     distance = results["distances"][0][idx]
    #     print(f"Found document chunk: {document} (ID: {doc_id}, Distance: {distance})")


# === REPLACED: OpenAI chat -> Ollama chat ===
def generate_response(question, relevant_chunks):
    context = "\n\n".join(relevant_chunks)
    prompt = (
        "You are an assistant for question-answering tasks. Use the following pieces of "
        "retrieved context to answer the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the answer concise."
        "\n\nContext:\n" + context + "\n\nQuestion:\n" + question
    )

    # Using Ollama chat; pull a chat model first: `ollama pull mistral` (or llama3)
    response = ollama.chat(
        model="mistral",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
    )

    # Return a minimal object with `.content` so your print() line remains unchanged
    return SimpleNamespace(content=response["message"]["content"])


question = "give me a brief overview of the articles. Be concise, please."
relevant_chunks = query_documents(question)
answer = generate_response(question, relevant_chunks)

print("==== Answer ====")
print(answer.content)
