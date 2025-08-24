import { promises as fs } from 'fs';
import path from 'path';

export interface ProcessedDocument {
  text: string;
  chunks: string[];
}

export class DocumentProcessor {
  private chunkSize: number;
  private chunkOverlap: number;

  constructor(chunkSize = 1024, chunkOverlap = 100) {
    this.chunkSize = chunkSize;
    this.chunkOverlap = chunkOverlap;
  }

  async processDocument(filePath: string, mimeType: string): Promise<ProcessedDocument> {
    let text = '';

    try {
      switch (mimeType) {
        case 'application/pdf':
          text = await this.processPDF(filePath);
          break;
        case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
          text = await this.processDOCX(filePath);
          break;
        case 'text/plain':
          text = await this.processTXT(filePath);
          break;
        default:
          throw new Error(`Unsupported file type: ${mimeType}`);
      }

      const chunks = this.createChunks(text);
      return { text, chunks };
    } catch (error) {
      throw new Error(`Failed to process document: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private async processPDF(filePath: string): Promise<string> {
    try {
      // For now, we'll use a simple text extraction approach
      // In a real implementation, you'd use pdf-parse or similar
      const pdfParse = await import('pdf-parse');
      const dataBuffer = await fs.readFile(filePath);
      const data = await pdfParse.default(dataBuffer);
      return data.text;
    } catch (error) {
      // Fallback if pdf-parse is not available
      throw new Error('PDF processing not available. Please install pdf-parse package.');
    }
  }

  private async processDOCX(filePath: string): Promise<string> {
    try {
      // For now, we'll use a simple text extraction approach
      // In a real implementation, you'd use mammoth or similar
      const mammoth = await import('mammoth');
      const result = await mammoth.extractRawText({ path: filePath });
      return result.value;
    } catch (error) {
      // Fallback if mammoth is not available
      throw new Error('DOCX processing not available. Please install mammoth package.');
    }
  }

  private async processTXT(filePath: string): Promise<string> {
    return await fs.readFile(filePath, 'utf-8');
  }

  private createChunks(text: string): string[] {
    const chunks: string[] = [];
    const words = text.split(/\s+/);
    
    for (let i = 0; i < words.length; i += this.chunkSize - this.chunkOverlap) {
      const chunk = words.slice(i, i + this.chunkSize).join(' ');
      if (chunk.trim()) {
        chunks.push(chunk.trim());
      }
    }

    return chunks;
  }

  setChunkSettings(chunkSize: number, chunkOverlap: number) {
    this.chunkSize = chunkSize;
    this.chunkOverlap = chunkOverlap;
  }
}
