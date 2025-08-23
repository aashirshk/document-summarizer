import numpy as np
from typing import List, Tuple, Dict, Any
import os
import requests
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import uuid
import json

class VectorStore:
    """Manages document embeddings and similarity search using Ollama."""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.embedding_model = "nomic-embed-text"  # Good embedding model for Ollama
        self.documents = {}  # document_id -> document_info
        self.embeddings = {}  # document_id -> list of embeddings
        self.chunks = {}     # document_id -> list of text chunks
        self.tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.tfidf_fitted = False
        
    def create_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """Create embeddings for text chunks using Ollama or TF-IDF fallback."""
        try:
            # Try Ollama first
            if self._check_ollama_available():
                return self._create_ollama_embeddings(text_chunks)
            else:
                # Fallback to TF-IDF if Ollama is not available
                return self._create_tfidf_embeddings(text_chunks)
            
        except Exception as e:
            # If everything fails, use TF-IDF as final fallback
            try:
                return self._create_tfidf_embeddings(text_chunks)
            except:
                raise Exception(f"Error creating embeddings: {str(e)}")
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running and has the embedding model."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                return any(self.embedding_model in name for name in model_names)
            return False
        except:
            return False
    
    def _create_ollama_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """Create embeddings using Ollama."""
        embeddings = []
        for chunk in text_chunks:
            data = {
                "model": self.embedding_model,
                "prompt": chunk
            }
            response = requests.post(f"{self.ollama_url}/api/embeddings", json=data)
            if response.status_code == 200:
                embedding = response.json()['embedding']
                embeddings.append(embedding)
            else:
                raise Exception(f"Ollama embedding failed: {response.text}")
        return embeddings
    
    def _create_tfidf_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """Create embeddings using TF-IDF as fallback."""
        # Combine all existing chunks for fitting if not already done
        all_chunks = text_chunks.copy()
        
        # Add existing chunks for better vocabulary
        for doc_chunks in self.chunks.values():
            all_chunks.extend(doc_chunks)
        
        if not self.tfidf_fitted or len(all_chunks) > 100:
            self.tfidf_vectorizer.fit(all_chunks)
            self.tfidf_fitted = True
        
        # Transform just the new chunks
        tfidf_matrix = self.tfidf_vectorizer.transform(text_chunks)
        try:
            # Handle scipy sparse matrices
            import scipy.sparse
            if scipy.sparse.issparse(tfidf_matrix):
                return tfidf_matrix.toarray().tolist()
            else:
                return tfidf_matrix.tolist()
        except ImportError:
            # Fallback if scipy not available
            if hasattr(tfidf_matrix, 'toarray'):
                return tfidf_matrix.toarray().tolist()
            else:
                return [[1.0] for _ in text_chunks]  # Simple fallback
    
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
            query_embedding = self.create_embeddings([query])[0]
            
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
            query_embedding = self.create_embeddings([query])[0]
            
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
