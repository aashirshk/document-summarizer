import { Document } from "@shared/schema";

export interface RAGSearchResult {
  documentId: string;
  documentName: string;
  chunk: string;
  confidence: number;
}

export interface VectorDocument {
  id: string;
  sessionId: string;
  documentId: string;
  documentName: string;
  chunk: string;
  embedding?: number[]; // In a real implementation, you'd compute embeddings
}

export class RAGService {
  private vectors: Map<string, VectorDocument>;
  private similarityThreshold: number;

  constructor(similarityThreshold = 0.7) {
    this.vectors = new Map();
    this.similarityThreshold = similarityThreshold;
  }

  async indexDocuments(documents: Document[]): Promise<void> {
    for (const doc of documents) {
      if (doc.chunks && doc.chunks.length > 0) {
        for (let i = 0; i < doc.chunks.length; i++) {
          const vectorDoc: VectorDocument = {
            id: `${doc.id}-${i}`,
            sessionId: doc.sessionId,
            documentId: doc.id,
            documentName: doc.originalName,
            chunk: doc.chunks[i],
          };
          this.vectors.set(vectorDoc.id, vectorDoc);
        }
      }
    }
  }

  async searchSimilar(query: string, sessionId: string, topK = 5): Promise<RAGSearchResult[]> {
    const sessionVectors = Array.from(this.vectors.values()).filter(
      v => v.sessionId === sessionId
    );

    // Simple keyword-based similarity for now
    // In a real implementation, you'd use embeddings and cosine similarity
    const results: RAGSearchResult[] = [];

    for (const vector of sessionVectors) {
      const similarity = this.calculateKeywordSimilarity(query, vector.chunk);
      
      if (similarity >= this.similarityThreshold) {
        results.push({
          documentId: vector.documentId,
          documentName: vector.documentName,
          chunk: vector.chunk,
          confidence: similarity,
        });
      }
    }

    // Sort by confidence and return top K
    return results
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, topK);
  }

  private calculateKeywordSimilarity(query: string, text: string): number {
    const queryWords = query.toLowerCase().split(/\s+/).filter(word => word.length > 2);
    const textWords = text.toLowerCase().split(/\s+/);
    
    if (queryWords.length === 0) return 0;

    let matches = 0;
    for (const queryWord of queryWords) {
      if (textWords.some(textWord => 
        textWord.includes(queryWord) || queryWord.includes(textWord)
      )) {
        matches++;
      }
    }

    return matches / queryWords.length;
  }

  setSimilarityThreshold(threshold: number): void {
    this.similarityThreshold = threshold;
  }

  clearSession(sessionId: string): void {
    const keysToDelete = Array.from(this.vectors.keys()).filter(
      key => this.vectors.get(key)?.sessionId === sessionId
    );
    
    for (const key of keysToDelete) {
      this.vectors.delete(key);
    }
  }
}

export const ragService = new RAGService();
