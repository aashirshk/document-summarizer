import os
from openai import OpenAI
from typing import List, Tuple

class RAGSystem:
    """Handles RAG-based document summarization and question answering."""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-4o"
    
    def summarize_document(self, content: str, max_length: int = 500) -> str:
        """Generate a comprehensive summary of a document."""
        try:
            # If content is very long, we might need to chunk it for summarization
            if len(content) > 8000:  # Leave room for prompt and response
                content = content[:8000] + "..."
            
            prompt = f"""
            Please provide a comprehensive summary of the following document. 
            Focus on the main topics, key findings, important concepts, and conclusions.
            Make the summary informative yet concise, around {max_length} words.
            
            Document content:
            {content}
            
            Summary:
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert document analyst. Provide clear, accurate, and comprehensive summaries that capture the essence of documents."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            return content.strip() if content else ""
            
        except Exception as e:
            raise Exception(f"Error generating summary: {str(e)}")
    
    def answer_question(self, question: str, relevant_chunks: List[Tuple[str, float, str]]) -> str:
        """Answer a question based on relevant document chunks."""
        try:
            if not relevant_chunks:
                return "I couldn't find relevant information in the uploaded documents to answer your question."
            
            # Prepare context from relevant chunks
            context_parts = []
            for i, (chunk, score, doc_name) in enumerate(relevant_chunks):
                context_parts.append(f"[Source {i+1} - {doc_name}]: {chunk}")
            
            context = "\n\n".join(context_parts)
            
            prompt = f"""
            Based on the following document excerpts, please answer the user's question accurately and comprehensively.
            If the information is not sufficient to answer the question, please say so.
            Always cite which source(s) you're using for your answer.
            
            Context from documents:
            {context}
            
            Question: {question}
            
            Answer:
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on provided document context. Always be accurate and cite your sources. If you cannot answer based on the context, say so clearly."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            content = response.choices[0].message.content
            return content.strip() if content else ""
            
        except Exception as e:
            raise Exception(f"Error answering question: {str(e)}")
    
    def generate_follow_up_questions(self, question: str, answer: str) -> List[str]:
        """Generate relevant follow-up questions based on the Q&A."""
        try:
            prompt = f"""
            Based on the following question and answer, suggest 3 relevant follow-up questions 
            that someone might want to ask to explore the topic further.
            
            Original Question: {question}
            Answer: {answer}
            
            Please provide exactly 3 follow-up questions, one per line:
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at generating thoughtful follow-up questions that help users explore topics more deeply."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=300,
                temperature=0.4
            )
            
            content = response.choices[0].message.content
            follow_up_text = content.strip() if content else ""
            follow_ups = [q.strip() for q in follow_up_text.split('\n') if q.strip()]
            
            return follow_ups[:3]  # Ensure we return at most 3 questions
            
        except Exception as e:
            # Return empty list if there's an error generating follow-ups
            return []
    
    def extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts and topics from document content."""
        try:
            if len(content) > 6000:
                content = content[:6000] + "..."
            
            prompt = f"""
            Analyze the following document content and extract 8-10 key concepts, topics, or themes.
            Return them as a simple list, one per line.
            
            Document content:
            {content}
            
            Key concepts:
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing documents and extracting key concepts and themes."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=400,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            concepts_text = content.strip() if content else ""
            concepts = [concept.strip().lstrip('- ').lstrip('* ') for concept in concepts_text.split('\n') if concept.strip()]
            
            return concepts[:10]  # Return at most 10 concepts
            
        except Exception as e:
            return []  # Return empty list if there's an error
