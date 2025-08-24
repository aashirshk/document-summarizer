import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertSessionSchema, insertDocumentSchema, insertQuerySchema } from "@shared/schema";
import multer from "multer";
import path from "path";
import { promises as fs } from "fs";
import { DocumentProcessor } from "./services/documentProcessor";
import { OllamaService } from "./services/ollamaService";
import { ragService } from "./services/ragService";

// Configure multer for file uploads
const upload = multer({
  dest: 'uploads/',
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain'
    ];
    
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only PDF, DOCX, and TXT files are allowed.'));
    }
  }
});

const documentProcessor = new DocumentProcessor();
const ollamaService = new OllamaService();

export async function registerRoutes(app: Express): Promise<Server> {
  // Session routes
  app.post("/api/sessions", async (req, res) => {
    try {
      const sessionData = insertSessionSchema.parse(req.body);
      const session = await storage.createSession(sessionData);
      res.json(session);
    } catch (error) {
      res.status(400).json({ 
        message: error instanceof Error ? error.message : "Invalid session data" 
      });
    }
  });

  app.get("/api/sessions/:id", async (req, res) => {
    try {
      const session = await storage.getSession(req.params.id);
      if (!session) {
        return res.status(404).json({ message: "Session not found" });
      }
      res.json(session);
    } catch (error) {
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to get session" 
      });
    }
  });

  app.patch("/api/sessions/:id", async (req, res) => {
    try {
      const session = await storage.updateSession(req.params.id, req.body);
      if (!session) {
        return res.status(404).json({ message: "Session not found" });
      }
      res.json(session);
    } catch (error) {
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to update session" 
      });
    }
  });

  app.post("/api/sessions/:id/end", async (req, res) => {
    try {
      const session = await storage.endSession(req.params.id);
      if (!session) {
        return res.status(404).json({ message: "Session not found" });
      }
      
      // Clear RAG data for this session
      ragService.clearSession(req.params.id);
      
      res.json(session);
    } catch (error) {
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to end session" 
      });
    }
  });

  // Document routes
  app.post("/api/sessions/:sessionId/documents", upload.single('file'), async (req, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({ message: "No file uploaded" });
      }

      const sessionId = req.params.sessionId;
      const session = await storage.getSession(sessionId);
      if (!session) {
        return res.status(404).json({ message: "Session not found" });
      }

      if (!session.isActive) {
        return res.status(400).json({ message: "Session is not active" });
      }

      // Check document limit
      const existingDocs = await storage.getDocumentsBySession(sessionId);
      if (existingDocs.length >= 10) {
        return res.status(400).json({ message: "Maximum document limit (10) reached" });
      }

      const documentData = {
        sessionId,
        filename: req.file.filename,
        originalName: req.file.originalname,
        mimeType: req.file.mimetype,
        size: req.file.size,
        status: "uploaded" as const,
      };

      const document = await storage.createDocument(documentData);

      // Process document asynchronously
      processDocumentAsync(document.id, req.file.path, req.file.mimetype);

      res.json(document);
    } catch (error) {
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to upload document" 
      });
    }
  });

  app.get("/api/sessions/:sessionId/documents", async (req, res) => {
    try {
      const documents = await storage.getDocumentsBySession(req.params.sessionId);
      res.json(documents);
    } catch (error) {
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to get documents" 
      });
    }
  });

  app.delete("/api/documents/:id", async (req, res) => {
    try {
      const document = await storage.getDocument(req.params.id);
      if (!document) {
        return res.status(404).json({ message: "Document not found" });
      }

      // Delete file from filesystem
      try {
        await fs.unlink(path.join('uploads', document.filename));
      } catch (error) {
        // File might not exist, continue with deletion
      }

      const deleted = await storage.deleteDocument(req.params.id);
      if (!deleted) {
        return res.status(404).json({ message: "Document not found" });
      }

      res.json({ message: "Document deleted successfully" });
    } catch (error) {
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to delete document" 
      });
    }
  });

  // Query routes
  app.post("/api/sessions/:sessionId/query", async (req, res) => {
    try {
      const { query } = req.body;
      if (!query || typeof query !== 'string') {
        return res.status(400).json({ message: "Query is required" });
      }

      const sessionId = req.params.sessionId;
      const session = await storage.getSession(sessionId);
      if (!session) {
        return res.status(404).json({ message: "Session not found" });
      }

      // Check if any documents are still processing
      const documents = await storage.getDocumentsBySession(sessionId);
      const processingDocs = documents.filter(doc => doc.status === "processing");
      
      if (processingDocs.length > 0) {
        return res.status(400).json({ 
          message: `Please wait - ${processingDocs.length} document(s) are still being processed` 
        });
      }

      const processedDocs = documents.filter(doc => doc.status === "processed");
      if (processedDocs.length === 0) {
        return res.json({
          response: "No processed documents found. Please upload and wait for documents to be processed before querying.",
          sources: []
        });
      }

      // Search for relevant document chunks
      const searchResults = await ragService.searchSimilar(query, sessionId, 5);
      
      if (searchResults.length === 0) {
        return res.json({
          response: "I couldn't find relevant information in the uploaded documents to answer your question. Try rephrasing your query or uploading more relevant documents.",
          sources: []
        });
      }

      // Get response from Ollama
      const context = searchResults.map(result => result.chunk);
      console.log('Attempting to query Ollama with context length:', context.length);
      let response;
      try {
        response = await ollamaService.queryDocuments({ query, context });
        console.log('Ollama response received successfully');
      } catch (ollamaError) {
        console.error('Ollama query failed:', ollamaError);
        // Fallback response when Ollama is not available
        response = `Based on the uploaded documents, I found relevant information related to your query: "${query}". However, the AI service is currently unavailable. The search found ${searchResults.length} relevant sections from your documents.`;
      }

      // Create query record
      const queryData = {
        sessionId,
        query,
        response,
        sources: searchResults.map(result => ({
          documentId: result.documentId,
          documentName: result.documentName,
          confidence: Math.round(result.confidence * 100)
        }))
      };

      const queryRecord = await storage.createQuery(queryData);

      res.json({
        response: queryRecord.response,
        sources: queryRecord.sources
      });
    } catch (error) {
      console.error('Query error:', error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to process query" 
      });
    }
  });

  app.post("/api/sessions/:sessionId/summarize", async (req, res) => {
    try {
      const sessionId = req.params.sessionId;
      const documents = await storage.getDocumentsBySession(sessionId);
      
      const processedDocs = documents.filter(doc => doc.status === "processed" && doc.extractedText);
      if (processedDocs.length === 0) {
        return res.status(400).json({ message: "No processed documents available for summarization" });
      }

      // Combine all document texts
      const combinedText = processedDocs.map(doc => `${doc.originalName}:\n${doc.extractedText}`).join('\n\n---\n\n');
      
      const summary = await ollamaService.summarizeText({ text: combinedText });

      res.json({ summary });
    } catch (error) {
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to generate summary" 
      });
    }
  });

  // Health check for Ollama
  app.get("/api/ollama/health", async (req, res) => {
    try {
      const isHealthy = await ollamaService.checkHealth();
      res.json({ 
        status: isHealthy ? "connected" : "disconnected",
        model: "llama3"
      });
    } catch (error) {
      res.status(500).json({ 
        status: "error",
        message: error instanceof Error ? error.message : "Health check failed" 
      });
    }
  });

  // Update RAG settings
  app.post("/api/sessions/:sessionId/rag-settings", async (req, res) => {
    try {
      const { chunkSize, chunkOverlap, similarityThreshold } = req.body;
      
      if (chunkSize) documentProcessor.setChunkSettings(chunkSize, chunkOverlap || 100);
      if (similarityThreshold) ragService.setSimilarityThreshold(similarityThreshold);
      
      res.json({ message: "RAG settings updated successfully" });
    } catch (error) {
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to update RAG settings" 
      });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}

// Async document processing function
async function processDocumentAsync(documentId: string, filePath: string, mimeType: string) {
  try {
    console.log(`Starting to process document ${documentId} with type ${mimeType}`);
    
    // Update status to processing
    await storage.updateDocument(documentId, { status: "processing" });

    // Process the document
    const processed = await documentProcessor.processDocument(filePath, mimeType);
    console.log(`Document ${documentId} processed successfully. Text length: ${processed.text.length}, Chunks: ${processed.chunks.length}`);

    // Update document with processed data
    await storage.updateDocument(documentId, {
      status: "processed",
      extractedText: processed.text,
      chunks: processed.chunks
    });

    // Index document for RAG
    const document = await storage.getDocument(documentId);
    if (document) {
      await ragService.indexDocuments([document]);
      console.log(`Document ${documentId} indexed for RAG successfully`);
    }

  } catch (error) {
    console.error(`Error processing document ${documentId}:`, error);
    
    const errorMessage = error instanceof Error ? error.message : "Unknown processing error";
    await storage.updateDocument(documentId, {
      status: "error",
      errorMessage
    });
  }
}
