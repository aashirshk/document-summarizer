import numpy as np
from typing import List, Tuple, Dict, Any
import os
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import uuid

class VectorStore:
    """Manages document embeddings and similarity search."""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.documents = {}  # document_id -> document_info
        self.embeddings = {}  # document_id -> list of embeddings
        self.chunks = {}     # document_id -> list of text chunks
        
    def create_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """Create embeddings for text chunks using OpenAI's embedding model."""
        try:
            embeddings = []
            # Process chunks in batches to avoid rate limits
            batch_size = 100
            
            for i in range(0, len(text_chunks), batch_size):
                batch = text_chunks[i:i + batch_size]
                
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",  # Using the newer embedding model
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            return embeddings
            
        except Exception as e:
            raise Exception(f"Error creating embeddings: {str(e)}")
    
    def add_document(self, document_name: str, chunks: List[str], embeddings: List[List[float]]) -> str:
        """Add a document with its chunks and embeddings to the store."""
        document_id = str(uuid.uuid4())
        
        self.documents[document_id] = {
            'name': document_name,
            'chunk_count': len(chunks),
            'created_at': np.datetime64('now')
        }
        
        self.chunks[document_id] = chunks
        self.embeddings[document_id] = embeddings
        
        return document_id
    
    def remove_document(self, document_id: str) -> bool:
        """Remove a document and its associated data from the store."""
        try:
            if document_id in self.documents:
                del self.documents[document_id]
                del self.chunks[document_id]
                del self.embeddings[document_id]
                return True
            return False
        except Exception:
            return False
    
    def similarity_search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, str]]:
        """Find the most similar chunks to the query."""
        try:
            # Create embedding for the query
            query_response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=[query]
            )
            query_embedding = query_response.data[0].embedding
            
            # Collect all chunks with their embeddings and metadata
            all_chunks = []
            all_embeddings = []
            chunk_metadata = []  # (document_id, chunk_index, document_name)
            
            for doc_id, doc_chunks in self.chunks.items():
                doc_embeddings = self.embeddings[doc_id]
                doc_name = self.documents[doc_id]['name']
                
                for i, (chunk, embedding) in enumerate(zip(doc_chunks, doc_embeddings)):
                    all_chunks.append(chunk)
                    all_embeddings.append(embedding)
                    chunk_metadata.append((doc_id, i, doc_name))
            
            if not all_embeddings:
                return []
            
            # Calculate similarities
            similarities = cosine_similarity([query_embedding], all_embeddings)[0]
            
            # Get top-k most similar chunks
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                chunk_text = all_chunks[idx]
                similarity_score = similarities[idx]
                doc_name = chunk_metadata[idx][2]
                
                results.append((chunk_text, similarity_score, doc_name))
            
            return results
            
        except Exception as e:
            raise Exception(f"Error performing similarity search: {str(e)}")
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about the stored documents."""
        total_docs = len(self.documents)
        total_chunks = sum(doc['chunk_count'] for doc in self.documents.values())
        
        return {
            'total_documents': total_docs,
            'total_chunks': total_chunks,
            'documents': list(self.documents.values())
        }
    
    def search_by_document(self, document_id: str, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Search for similar chunks within a specific document."""
        try:
            if document_id not in self.documents:
                return []
            
            # Create embedding for the query
            query_response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=[query]
            )
            query_embedding = query_response.data[0].embedding
            
            # Get chunks and embeddings for this document
            doc_chunks = self.chunks[document_id]
            doc_embeddings = self.embeddings[document_id]
            
            # Calculate similarities
            similarities = cosine_similarity([query_embedding], doc_embeddings)[0]
            
            # Get top-k most similar chunks
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                chunk_text = doc_chunks[idx]
                similarity_score = similarities[idx]
                results.append((chunk_text, similarity_score))
            
            return results
            
        except Exception as e:
            raise Exception(f"Error searching within document: {str(e)}")
