import PyPDF2
import docx
import os
import re
from typing import List, Tuple

class DocumentProcessor:
    """Handles document content extraction and preprocessing."""
    
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 200
    
    def extract_content(self, file_path: str, file_type: str) -> str:
        """Extract text content from different file formats."""
        try:
            if file_type == "application/pdf" or file_path.endswith('.pdf'):
                return self._extract_pdf_content(file_path)
            elif file_type == "text/plain" or file_path.endswith('.txt'):
                return self._extract_txt_content(file_path)
            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_path.endswith('.docx'):
                return self._extract_docx_content(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            raise Exception(f"Error extracting content from {file_path}: {str(e)}")
    
    def _extract_pdf_content(self, file_path: str) -> str:
        """Extract text from PDF files using PyPDF2."""
        content = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    content += page.extract_text() + "\n"
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
        
        return self._clean_text(content)
    
    def _extract_txt_content(self, file_path: str) -> str:
        """Extract text from plain text files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
        except Exception as e:
            raise Exception(f"Error reading text file: {str(e)}")
        
        return self._clean_text(content)
    
    def _extract_docx_content(self, file_path: str) -> str:
        """Extract text from DOCX files."""
        try:
            doc = docx.Document(file_path)
            content = ""
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
        except Exception as e:
            raise Exception(f"Error reading DOCX file: {str(e)}")
        
        return self._clean_text(content)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-\'""]', ' ', text)
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks for better context preservation."""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Find end position
            end = start + self.chunk_size
            
            # If we're not at the end of the text, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings in the last 200 characters of the chunk
                search_start = max(start + self.chunk_size - 200, start)
                sentence_ends = []
                
                for match in re.finditer(r'[.!?]\s+', text[search_start:end]):
                    sentence_ends.append(search_start + match.end())
                
                if sentence_ends:
                    end = sentence_ends[-1]  # Use the last sentence boundary
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            if end >= len(text):
                break
            start = end - self.chunk_overlap
        
        return chunks
    
    def get_document_metadata(self, file_path: str) -> dict:
        """Extract basic metadata from document."""
        file_size = os.path.getsize(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        return {
            'file_size': file_size,
            'file_extension': file_extension,
            'file_name': os.path.basename(file_path)
        }
