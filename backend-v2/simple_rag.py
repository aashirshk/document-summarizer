import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
import os
from dotenv import load_dotenv
import PyPDF2
import uuid

# Load environment variables
load_dotenv()

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200



class EmbeddingModel:
    def __init__(self, model_type="nomic-embed-text"):
        self.embedding_fn = embedding_functions.OllamaEmbeddingFunction(
            api_key="ollama"
            model_name="nomic-embed-text",                    
            api_base="http://localhost:11434/v1",       
        )

class LLMModel:
    def __init__(self, model_type="ollama"):
        self.model_type = model_type
        if model_type == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model_name = "gpt-4o-mini"
        elif model_type == "ollama":
            self.client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            self.model_name = "llama3.2"

    def generate_completion(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.0,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"

