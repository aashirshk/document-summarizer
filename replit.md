# Multi-Document RAG System

## Overview

This is a Context-Aware Multi-Document RAG (Retrieval-Augmented Generation) System built with Streamlit. The application enables users to upload multiple documents in various formats (PDF, TXT, DOCX) and provides AI-powered document summarization and question-answering capabilities. The system processes documents into chunks, creates vector embeddings for semantic search, and uses OpenAI's GPT models to generate intelligent responses based on document context.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Streamlit-based Web Interface**: Single-page application with sidebar navigation for document management and main area for interaction
- **Session State Management**: Persistent storage of documents, vector store, and RAG system instances across user sessions
- **Real-time Processing**: Live document upload and processing with progress indicators

### Document Processing Pipeline
- **Multi-format Support**: Handles PDF (PyPDF2), DOCX (python-docx), and plain text files
- **Content Extraction**: Format-specific text extraction with error handling and text cleaning
- **Chunking Strategy**: Fixed-size chunking with overlap (1000 characters, 200 overlap) for better context preservation
- **Preprocessing**: Text cleaning and normalization to improve embedding quality

### Vector Storage and Retrieval
- **In-Memory Vector Store**: Custom implementation using NumPy arrays and scikit-learn for similarity computation
- **OpenAI Embeddings**: Uses `text-embedding-3-small` model for generating document embeddings
- **Cosine Similarity Search**: Efficient semantic search across document chunks
- **Document Indexing**: UUID-based document identification with metadata storage

### RAG System Design
- **Dual Functionality**: Supports both document summarization and context-aware question answering
- **GPT-4o Integration**: Uses the latest OpenAI model for high-quality text generation
- **Context Window Management**: Automatic content truncation for large documents to fit model limits
- **Temperature Control**: Low temperature (0.3) for consistent, factual responses

### Error Handling and Validation
- **API Key Validation**: Environment variable checking with user-friendly error messages
- **File Type Validation**: Strict file format checking before processing
- **Graceful Degradation**: Comprehensive error handling with informative user feedback

## External Dependencies

### AI Services
- **OpenAI API**: Core dependency for embeddings (`text-embedding-3-small`) and text generation (`gpt-4o`)
- **API Key Management**: Requires `OPENAI_API_KEY` environment variable

### Document Processing Libraries
- **PyPDF2**: PDF text extraction and processing
- **python-docx**: Microsoft Word document (.docx) processing
- **Built-in text handling**: Plain text file processing

### Machine Learning and Data Processing
- **NumPy**: Numerical operations for embedding storage and manipulation
- **scikit-learn**: Cosine similarity calculations for semantic search
- **UUID**: Unique document identification and management

### Web Framework
- **Streamlit**: Complete web application framework with built-in session management and UI components

### System Requirements
- **tempfile**: Temporary file handling for uploaded documents
- **os**: Environment variable access and system operations
- **re**: Regular expression support for text cleaning and preprocessing