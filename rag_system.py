import os
import requests
import json
from typing import List, Tuple

class RAGSystem:
    """Handles RAG-based document summarization and question answering using Llama."""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model = "llama3.1:latest"  # Llama 3.1 as it's more widely available
        self.model_llama5 = "llama3.2:latest"  # We'll try Llama 5 first, fallback to 3.1
    
    def summarize_document(self, content: str, max_length: int = 500) -> str:
        """Generate a comprehensive summary of a document using Llama."""
        try:
            # If content is very long, we might need to chunk it for summarization
            if len(content) > 8000:  # Leave room for prompt and response
                content = content[:8000] + "..."
            
            prompt = f"""You are an expert document analyst. Provide clear, accurate, and comprehensive summaries that capture the essence of documents.

Please provide a comprehensive summary of the following document. 
Focus on the main topics, key findings, important concepts, and conclusions.
Make the summary informative yet concise, around {max_length} words.

Document content:
{content}

Summary:"""
            
            response = self._call_llama(prompt)
            return response.strip() if response else ""
            
        except Exception as e:
            raise Exception(f"Error generating summary: {str(e)}")
    
    def _call_llama(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call Ollama API with Llama model."""
        try:
            # First try to use available model
            available_model = self._get_available_model()
            
            data = {
                "model": available_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": max_tokens
                }
            }
            
            response = requests.post(f"{self.ollama_url}/api/generate", json=data, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to Ollama. Please make sure Ollama is running on http://localhost:11434")
        except Exception as e:
            raise Exception(f"Error calling Llama model: {str(e)}")
    
    def _get_available_model(self) -> str:
        """Get the best available Llama model."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                # Try Llama models in order of preference
                preferred_models = [
                    "llama3.2:latest", "llama3.2", 
                    "llama3.1:latest", "llama3.1",
                    "llama2:latest", "llama2"
                ]
                
                for preferred in preferred_models:
                    for available in model_names:
                        if preferred in available:
                            return available
                
                # If no Llama model found, use the first available model
                if model_names:
                    return model_names[0]
                else:
                    raise Exception("No models available in Ollama")
            else:
                raise Exception("Cannot fetch Ollama models")
        except:
            # Fallback to default
            return self.model
    
    def answer_question(self, question: str, relevant_chunks: List[Tuple[str, float, str]]) -> str:
        """Answer a question based on relevant document chunks using Llama."""
        try:
            if not relevant_chunks:
                return "I couldn't find relevant information in the uploaded documents to answer your question."
            
            # Prepare context from relevant chunks
            context_parts = []
            for i, (chunk, score, doc_name) in enumerate(relevant_chunks):
                context_parts.append(f"[Source {i+1} - {doc_name}]: {chunk}")
            
            context = "\n\n".join(context_parts)
            
            prompt = f"""You are a helpful assistant that answers questions based on provided document context. Always be accurate and cite your sources. If you cannot answer based on the context, say so clearly.

Based on the following document excerpts, please answer the user's question accurately and comprehensively.
If the information is not sufficient to answer the question, please say so.
Always cite which source(s) you're using for your answer.

Context from documents:
{context}

Question: {question}

Answer:"""
            
            response = self._call_llama(prompt, max_tokens=1000)
            return response.strip() if response else ""
            
        except Exception as e:
            raise Exception(f"Error answering question: {str(e)}")
    
    def generate_follow_up_questions(self, question: str, answer: str) -> List[str]:
        """Generate relevant follow-up questions based on the Q&A using Llama."""
        try:
            prompt = f"""You are an expert at generating thoughtful follow-up questions that help users explore topics more deeply.

Based on the following question and answer, suggest 3 relevant follow-up questions 
that someone might want to ask to explore the topic further.

Original Question: {question}
Answer: {answer}

Please provide exactly 3 follow-up questions, one per line:"""
            
            response = self._call_llama(prompt, max_tokens=300)
            follow_up_text = response.strip() if response else ""
            follow_ups = [q.strip() for q in follow_up_text.split('\n') if q.strip()]
            
            return follow_ups[:3]  # Ensure we return at most 3 questions
            
        except Exception as e:
            # Return empty list if there's an error generating follow-ups
            return []
    
    def extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts and topics from document content using Llama."""
        try:
            if len(content) > 6000:
                content = content[:6000] + "..."
            
            prompt = f"""You are an expert at analyzing documents and extracting key concepts and themes.

Analyze the following document content and extract 8-10 key concepts, topics, or themes.
Return them as a simple list, one per line.

Document content:
{content}

Key concepts:"""
            
            response = self._call_llama(prompt, max_tokens=400)
            concepts_text = response.strip() if response else ""
            concepts = [concept.strip().lstrip('- ').lstrip('* ') for concept in concepts_text.split('\n') if concept.strip()]
            
            return concepts[:10]  # Return at most 10 concepts
            
        except Exception as e:
            return []  # Return empty list if there's an error
