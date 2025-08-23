# Multi-Document RAG System

## Overview

This is a Context-Aware Multi-Document RAG (Retrieval-Augmented Generation) System built with Streamlit. The application enables users to upload multiple documents in various formats (PDF, TXT, DOCX) and provides AI-powered document summarization and question-answering capabilities. The system processes documents into chunks, creates vector embeddings for semantic search, and uses OpenAI's GPT models to generate intelligent responses based on document context.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (August 23, 2025)

✓ **MAJOR UPDATE**: Replaced OpenAI with Llama models via Ollama
✓ Eliminated API quota limits and costs - now completely free to run
✓ Added TF-IDF fallback for when Ollama is not available
✓ Smart error handling with graceful degradation
✓ Updated UI to show Ollama connection status and available models
✓ System works locally without any external API dependencies

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
- **Ollama/TF-IDF Embeddings**: Uses Ollama for Llama model embeddings or TF-IDF fallback for document embeddings
- **Cosine Similarity Search**: Efficient semantic search across document chunks
- **Document Indexing**: UUID-based document identification with metadata storage

### RAG System Design
- **Dual Functionality**: Supports both document summarization and context-aware question answering
- **Llama Integration**: Uses local Llama models (3.1/3.2) via Ollama for high-quality text generation
- **Context Window Management**: Automatic content truncation for large documents to fit model limits
- **Temperature Control**: Low temperature (0.3) for consistent, factual responses

### Error Handling and Validation
- **Ollama Connection Validation**: Local service checking with fallback to TF-IDF when unavailable
- **File Type Validation**: Strict file format checking before processing
- **Graceful Degradation**: Comprehensive error handling with informative user feedback

## External Dependencies

### AI Services
- **Ollama (Optional)**: Local AI inference for Llama models (llama3.1, llama3.2) for embeddings and text generation
- **TF-IDF Fallback**: Built-in text similarity using scikit-learn when Ollama is not available
- **No API Keys Required**: Completely local and free to run

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