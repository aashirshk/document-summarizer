import PyPDF2
import uuid
from typing import List, Dict

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


class ImprovedPDFProcessor:
    def __init__(self, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def read_pdf(self, pdf_file) -> str:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            try:
                text += page.extract_text() + "\n"
            except Exception as e:
                print(f"Error reading page: {e}")
        return text

    def create_chunks(self, text: str, filename: str) -> List[Dict]:
        chunks = []
        start = 0
        chunk_count = 0

        while start < len(text):
            end = start + self.chunk_size
            if start > 0:
                start = start - self.chunk_overlap

            chunk = text[start:end]

            if end < len(text):
                last_period = chunk.rfind(".")
                if last_period != -1:
                    chunk = chunk[: last_period + 1]
                    end = start + last_period + 1

            chunks.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "metadata": {"source": filename, "chunk_index": chunk_count},
            })

            start = end
            chunk_count += 1

        return chunks
