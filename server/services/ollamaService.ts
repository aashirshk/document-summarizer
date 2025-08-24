export interface OllamaResponse {
  response: string;
  done: boolean;
}

export interface SummarizationRequest {
  text: string;
  maxLength?: number;
}

export interface QueryRequest {
  query: string;
  context: string[];
}

export class OllamaService {
  private baseUrl: string;
  private model: string;

  constructor() {
    this.baseUrl = process.env.OLLAMA_BASE_URL || 'http://localhost:11434';
    this.model = process.env.OLLAMA_MODEL || 'llama3';
  }

  async summarizeText(request: SummarizationRequest): Promise<string> {
    const { text, maxLength = 500 } = request;
    
    const prompt = `Please provide a concise summary of the following text in approximately ${maxLength} words. Focus on the main points and key insights:

${text}

Summary:`;

    try {
      const response = await this.generateCompletion(prompt);
      return response.trim();
    } catch (error) {
      throw new Error(`Failed to summarize text: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async queryDocuments(request: QueryRequest): Promise<string> {
    const { query, context } = request;
    
    const contextText = context.join('\n\n---\n\n');
    const prompt = `Based on the following document excerpts, please answer the question. If the answer cannot be found in the provided context, please say so.

Context:
${contextText}

Question: ${query}

Answer:`;

    try {
      const response = await this.generateCompletion(prompt);
      return response.trim();
    } catch (error) {
      throw new Error(`Failed to query documents: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async generateCompletion(prompt: string): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: this.model,
          prompt: prompt,
          stream: false,
        }),
      });

      if (!response.ok) {
        throw new Error(`Ollama API error: ${response.status} ${response.statusText}`);
      }

      const data: OllamaResponse = await response.json();
      return data.response;
    } catch (error) {
      if (error instanceof Error && error.message.includes('fetch')) {
        throw new Error('Unable to connect to Ollama. Please ensure Ollama is running and accessible.');
      }
      throw error;
    }
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`);
      return response.ok;
    } catch (error) {
      return false;
    }
  }
}
