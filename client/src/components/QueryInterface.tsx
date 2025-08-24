import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Search, List } from "lucide-react";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface QueryInterfaceProps {
  sessionId: string;
}

interface QueryResponse {
  response: string;
  sources: Array<{
    documentId: string;
    documentName: string;
    confidence: number;
  }>;
}

export default function QueryInterface({ sessionId }: QueryInterfaceProps) {
  const { toast } = useToast();
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [sources, setSources] = useState<QueryResponse['sources']>([]);

  const queryMutation = useMutation({
    mutationFn: async (queryText: string) => {
      const response = await apiRequest('POST', `/api/sessions/${sessionId}/query`, {
        query: queryText,
      });
      return response.json() as Promise<QueryResponse>;
    },
    onSuccess: (data) => {
      setResponse(data.response);
      setSources(data.sources);
    },
    onError: (error) => {
      toast({
        title: "Query failed",
        description: error instanceof Error ? error.message : "Failed to process query",
        variant: "destructive",
      });
    },
  });

  const summarizeMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest('POST', `/api/sessions/${sessionId}/summarize`);
      return response.json();
    },
    onSuccess: (data) => {
      setResponse(data.summary);
      setSources([]);
      setQuery("Generate a comprehensive summary of all uploaded documents");
    },
    onError: (error) => {
      toast({
        title: "Summarization failed",
        description: error instanceof Error ? error.message : "Failed to generate summary",
        variant: "destructive",
      });
    },
  });

  const handleSubmitQuery = () => {
    if (!query.trim()) {
      toast({
        title: "Query required",
        description: "Please enter a question to search the documents",
        variant: "destructive",
      });
      return;
    }
    queryMutation.mutate(query.trim());
  };

  const handleSummarizeAll = () => {
    summarizeMutation.mutate();
  };

  return (
    <div className="mt-8 bg-white rounded-xl shadow-sm border border-slate-200 p-6" data-testid="query-interface">
      <h2 className="text-xl font-semibold text-slate-900 mb-6" data-testid="query-interface-title">
        Document Query Interface
      </h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Query Input */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Ask a question about your documents
            </label>
            <Textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., What are the main findings from the research paper?"
              className="resize-none focus:ring-2 focus:ring-primary focus:border-transparent"
              rows={4}
              data-testid="input-query"
            />
          </div>
          
          <div className="flex space-x-3">
            <Button
              onClick={handleSubmitQuery}
              disabled={queryMutation.isPending || !query.trim()}
              className="flex-1 bg-primary text-white hover:bg-blue-700"
              data-testid="button-submit-query"
            >
              <Search className="w-4 h-4 mr-2" />
              {queryMutation.isPending ? 'Querying...' : 'Query Documents'}
            </Button>
            <Button
              onClick={handleSummarizeAll}
              disabled={summarizeMutation.isPending}
              variant="outline"
              className="bg-slate-600 text-white hover:bg-slate-700"
              data-testid="button-summarize-all"
            >
              <List className="w-4 h-4 mr-2" />
              {summarizeMutation.isPending ? 'Summarizing...' : 'Summarize All'}
            </Button>
          </div>
        </div>

        {/* Response Area */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              AI Response
            </label>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 min-h-[160px]" data-testid="response-area">
              {(queryMutation.isPending || summarizeMutation.isPending) ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mr-3"></div>
                  <span className="text-sm text-slate-600">
                    {queryMutation.isPending ? 'Processing query...' : 'Generating summary...'}
                  </span>
                </div>
              ) : response ? (
                <div className="text-sm text-slate-700 whitespace-pre-wrap" data-testid="response-text">
                  {response}
                </div>
              ) : (
                <div className="text-sm text-slate-600" data-testid="response-placeholder">
                  Response will appear here after submitting a query...
                </div>
              )}
            </div>
          </div>
          
          {/* Source References */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Source References
            </label>
            <div className="space-y-2" data-testid="source-references">
              {sources.length > 0 ? (
                sources.map((source, index) => (
                  <div
                    key={`${source.documentId}-${index}`}
                    className="flex items-center justify-between p-2 bg-blue-50 rounded border border-blue-200"
                    data-testid={`source-reference-${index}`}
                  >
                    <span className="text-sm text-blue-800 truncate" data-testid={`source-document-${index}`}>
                      {source.documentName}
                    </span>
                    <Badge
                      variant="secondary"
                      className="text-xs text-blue-600 bg-blue-100"
                      data-testid={`source-confidence-${index}`}
                    >
                      {source.confidence}% match
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-500 p-2" data-testid="no-sources">
                  {response ? 'No specific sources referenced' : 'Sources will appear here after querying'}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
