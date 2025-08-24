# Overview

A document-aware RAG (Retrieval-Augmented Generation) application that allows users to upload documents, process them into searchable chunks, and query their content using natural language. The system integrates with Ollama for local LLM inference and provides a clean web interface for document management and AI-powered querying.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **React with TypeScript**: Modern component-based frontend using React 18 with full TypeScript support
- **Vite Build System**: Fast development server and optimized production builds
- **shadcn/ui Components**: Comprehensive UI component library built on Radix UI primitives
- **TanStack Query**: Server state management with caching, background updates, and optimistic updates
- **Wouter**: Lightweight client-side routing solution
- **Tailwind CSS**: Utility-first CSS framework with custom design system variables

## Backend Architecture
- **Express.js Server**: RESTful API server with middleware for logging, error handling, and file uploads
- **TypeScript**: Full type safety across server-side code
- **Modular Services**: Separation of concerns with dedicated services for document processing, LLM integration, and RAG functionality
- **Session-based Architecture**: Temporary sessions to manage document collections and queries
- **File Upload Handling**: Multer integration for secure file uploads with size and type validation

## Data Storage Solutions
- **Drizzle ORM**: Type-safe database toolkit configured for PostgreSQL
- **PostgreSQL Database**: Relational database for structured data storage
- **Neon Database**: Cloud-hosted PostgreSQL service
- **In-Memory Storage**: Fallback storage implementation for development and testing
- **File System Storage**: Temporary file storage for uploaded documents during processing

## Document Processing Pipeline
- **Multi-format Support**: PDF, DOCX, and TXT file processing capabilities
- **Text Extraction**: Dedicated document processor service for content extraction
- **Chunking Strategy**: Configurable text chunking with overlap for optimal retrieval
- **Vector Storage**: In-memory vector storage for semantic search (expandable to external vector databases)

## AI Integration
- **Ollama Service**: Local LLM inference using Ollama with configurable models
- **RAG Implementation**: Custom retrieval-augmented generation with similarity-based document chunk retrieval
- **Dual AI Modes**: Document summarization and question-answering capabilities
- **Streaming Support**: Prepared for streaming LLM responses

## API Design
- **RESTful Endpoints**: Standard REST patterns for CRUD operations
- **Session Management**: `/api/sessions` endpoints for session lifecycle
- **Document Operations**: `/api/documents` and `/api/sessions/:id/documents` for file management
- **Query Interface**: `/api/sessions/:id/query` and `/api/sessions/:id/summarize` for AI interactions
- **Health Monitoring**: `/api/ollama/health` for service status checking

# External Dependencies

## Core Framework Dependencies
- **Express.js**: Web application framework for Node.js
- **React**: Frontend UI library with TypeScript support
- **Vite**: Build tool and development server

## Database and ORM
- **Drizzle ORM**: TypeScript ORM for database operations
- **@neondatabase/serverless**: Serverless PostgreSQL client for Neon database
- **connect-pg-simple**: PostgreSQL session store for Express sessions

## AI and ML Services
- **Ollama**: Local LLM inference server (external service)
- **pdf-parse**: PDF text extraction library
- **Custom RAG Service**: In-house retrieval-augmented generation implementation

## UI and Styling
- **shadcn/ui**: Comprehensive component library built on Radix UI
- **Radix UI**: Headless UI component primitives
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Icon library

## Development and Build Tools
- **TypeScript**: Type safety across the entire application
- **ESBuild**: Fast JavaScript bundler for production builds
- **PostCSS**: CSS processing with Tailwind and Autoprefixer

## File Processing
- **Multer**: Middleware for handling multipart/form-data file uploads
- **Node.js File System**: Built-in file system operations for document storage

## State Management and HTTP
- **TanStack React Query**: Server state management and data fetching
- **Wouter**: Lightweight routing for React
- **Native Fetch API**: HTTP client for API communication