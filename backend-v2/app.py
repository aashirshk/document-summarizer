import chromadb
from chromadb.utils import embedding_functions


client = chromadb.Client()

default_ef = embedding_functions.DefaultEmbeddingFunction()

collection = client.get_or_create_collection("test_collection", embedding_function=default_ef)

documents = [
    {"id": "doc1", "text": "Hello, world!"},
    {"id": "doc2", "text": "How are you today?"},
    {"id": "doc3", "text": "Goodbye, see you later!"},
    {"id": "doc4", "text": "Hello, There. It is good to see you around!"},
]

for document in documents:
    collection.upsert(ids=[document["id"]], documents=[document["text"]])

query = "Are you good today!"
results = collection.query(query_texts=[query], n_results=4)


for idx, document in enumerate(results["documents"][0]):
    doc_id = results["ids"][0][idx]
    distance = results["distances"][0][idx]
    print(f"For the query: {query}\nFound the the document: {document} with id: {doc_id} has a distance of {distance}")
