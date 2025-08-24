import { type Session, type InsertSession, type Document, type InsertDocument, type Query, type InsertQuery } from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  // Session methods
  createSession(session: InsertSession): Promise<Session>;
  getSession(id: string): Promise<Session | undefined>;
  updateSession(id: string, updates: Partial<Session>): Promise<Session | undefined>;
  endSession(id: string): Promise<Session | undefined>;

  // Document methods
  createDocument(document: InsertDocument): Promise<Document>;
  getDocument(id: string): Promise<Document | undefined>;
  getDocumentsBySession(sessionId: string): Promise<Document[]>;
  updateDocument(id: string, updates: Partial<Document>): Promise<Document | undefined>;
  deleteDocument(id: string): Promise<boolean>;

  // Query methods
  createQuery(query: InsertQuery): Promise<Query>;
  getQueriesBySession(sessionId: string): Promise<Query[]>;
}

export class MemStorage implements IStorage {
  private sessions: Map<string, Session>;
  private documents: Map<string, Document>;
  private queries: Map<string, Query>;

  constructor() {
    this.sessions = new Map();
    this.documents = new Map();
    this.queries = new Map();
  }

  async createSession(insertSession: InsertSession): Promise<Session> {
    const id = randomUUID();
    const session: Session = {
      ...insertSession,
      id,
      startTime: new Date(),
      endTime: null,
      isActive: true,
      documentCount: 0,
      totalSize: 0,
    };
    this.sessions.set(id, session);
    return session;
  }

  async getSession(id: string): Promise<Session | undefined> {
    return this.sessions.get(id);
  }

  async updateSession(id: string, updates: Partial<Session>): Promise<Session | undefined> {
    const session = this.sessions.get(id);
    if (!session) return undefined;
    
    const updatedSession = { ...session, ...updates };
    this.sessions.set(id, updatedSession);
    return updatedSession;
  }

  async endSession(id: string): Promise<Session | undefined> {
    const session = this.sessions.get(id);
    if (!session) return undefined;
    
    const updatedSession = { ...session, endTime: new Date(), isActive: false };
    this.sessions.set(id, updatedSession);
    return updatedSession;
  }

  async createDocument(insertDocument: InsertDocument): Promise<Document> {
    const id = randomUUID();
    const document: Document = {
      ...insertDocument,
      id,
      status: insertDocument.status || "uploaded",
      uploadedAt: new Date(),
      processedAt: null,
      extractedText: null,
      chunks: [],
      errorMessage: null,
    };
    this.documents.set(id, document);

    // Update session document count and total size
    const session = this.sessions.get(insertDocument.sessionId);
    if (session) {
      const updatedSession = {
        ...session,
        documentCount: session.documentCount + 1,
        totalSize: session.totalSize + insertDocument.size,
      };
      this.sessions.set(insertDocument.sessionId, updatedSession);
    }

    return document;
  }

  async getDocument(id: string): Promise<Document | undefined> {
    return this.documents.get(id);
  }

  async getDocumentsBySession(sessionId: string): Promise<Document[]> {
    return Array.from(this.documents.values()).filter(doc => doc.sessionId === sessionId);
  }

  async updateDocument(id: string, updates: Partial<Document>): Promise<Document | undefined> {
    const document = this.documents.get(id);
    if (!document) return undefined;
    
    const updatedDocument = { ...document, ...updates };
    if (updates.status === "processed" && !document.processedAt) {
      updatedDocument.processedAt = new Date();
    }
    
    this.documents.set(id, updatedDocument);
    return updatedDocument;
  }

  async deleteDocument(id: string): Promise<boolean> {
    const document = this.documents.get(id);
    if (!document) return false;

    this.documents.delete(id);

    // Update session document count and total size
    const session = this.sessions.get(document.sessionId);
    if (session) {
      const updatedSession = {
        ...session,
        documentCount: session.documentCount - 1,
        totalSize: session.totalSize - document.size,
      };
      this.sessions.set(document.sessionId, updatedSession);
    }

    return true;
  }

  async createQuery(insertQuery: InsertQuery): Promise<Query> {
    const id = randomUUID();
    const query: Query = {
      ...insertQuery,
      id,
      response: insertQuery.response || null,
      sources: insertQuery.sources ? (Array.isArray(insertQuery.sources) ? insertQuery.sources : []) : [],
      createdAt: new Date(),
    };
    this.queries.set(id, query);
    return query;
  }

  async getQueriesBySession(sessionId: string): Promise<Query[]> {
    return Array.from(this.queries.values()).filter(query => query.sessionId === sessionId);
  }
}

export const storage = new MemStorage();
