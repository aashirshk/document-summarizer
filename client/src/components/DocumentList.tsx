import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, File, FileType, Trash2, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import type { Document } from "@shared/schema";

interface DocumentListProps {
  sessionId: string;
  onProceedToQuery: () => void;
}

export default function DocumentList({ sessionId, onProceedToQuery }: DocumentListProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: documents = [], isLoading } = useQuery<Document[]>({
    queryKey: ['/api/sessions', sessionId, 'documents'],
    refetchInterval: 2000, // Poll every 2 seconds for status updates
  });

  const deleteMutation = useMutation({
    mutationFn: async (documentId: string) => {
      await apiRequest('DELETE', `/api/documents/${documentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/sessions', sessionId, 'documents'] });
      toast({
        title: "Document deleted",
        description: "Document has been removed successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Delete failed",
        description: error instanceof Error ? error.message : "Failed to delete document",
        variant: "destructive",
      });
    },
  });

  const clearAllMutation = useMutation({
    mutationFn: async () => {
      await Promise.all(documents.map(doc => 
        apiRequest('DELETE', `/api/documents/${doc.id}`)
      ));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/sessions', sessionId, 'documents'] });
      toast({
        title: "All documents cleared",
        description: "All documents have been removed successfully",
      });
    },
  });

  const getFileIcon = (mimeType: string) => {
    switch (mimeType) {
      case 'application/pdf':
        return <File className="text-red-600" />;
      case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        return <FileText className="text-blue-600" />;
      case 'text/plain':
        return <FileType className="text-slate-600" />;
      default:
        return <FileText className="text-slate-600" />;
    }
  };

  const getFileIconBg = (mimeType: string) => {
    switch (mimeType) {
      case 'application/pdf':
        return 'bg-red-100';
      case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        return 'bg-blue-100';
      case 'text/plain':
        return 'bg-slate-100';
      default:
        return 'bg-slate-100';
    }
  };

  const getStatusBadge = (status: string, errorMessage?: string | null) => {
    switch (status) {
      case 'processed':
        return (
          <Badge className="bg-success text-white" data-testid={`status-processed`}>
            <Check className="w-3 h-3 mr-1" />
            PROCESSED
          </Badge>
        );
      case 'processing':
        return (
          <Badge className="bg-warning text-white" data-testid={`status-processing`}>
            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            PROCESSING
          </Badge>
        );
      case 'error':
        return (
          <Badge variant="destructive" title={errorMessage || 'Processing error'} data-testid={`status-error`}>
            ERROR
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary" data-testid={`status-uploaded`}>
            UPLOADED
          </Badge>
        );
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const processedCount = documents.filter(doc => doc.status === 'processed').length;
  const processingCount = documents.filter(doc => doc.status === 'processing').length;
  const totalCount = documents.length;
  const progressPercentage = totalCount > 0 ? (processedCount / totalCount) * 100 : 0;
  const allProcessed = totalCount > 0 && processedCount === totalCount;

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6" data-testid="document-list-loading">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-slate-200 rounded w-1/3"></div>
          <div className="space-y-3">
            <div className="h-16 bg-slate-200 rounded"></div>
            <div className="h-16 bg-slate-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6" data-testid="document-list-section">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-900" data-testid="document-list-title">
          Uploaded Documents{' '}
          <span className="text-sm font-normal text-slate-500" data-testid="document-count">
            ({totalCount}/10)
          </span>
        </h3>
        {totalCount > 0 && (
          <Button
            variant="ghost"
            onClick={() => clearAllMutation.mutate()}
            disabled={clearAllMutation.isPending}
            className="text-sm text-slate-500 hover:text-error"
            data-testid="button-clear-all"
          >
            Clear All
          </Button>
        )}
      </div>

      {totalCount === 0 ? (
        <div className="text-center py-8 text-slate-500" data-testid="empty-document-list">
          <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300" />
          <p>No documents uploaded yet</p>
          <p className="text-sm">Upload documents to get started</p>
        </div>
      ) : (
        <>
          <div className="space-y-3" data-testid="document-items">
            {documents.map((document) => (
              <div
                key={document.id}
                className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200"
                data-testid={`document-item-${document.id}`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${getFileIconBg(document.mimeType)}`}>
                    {getFileIcon(document.mimeType)}
                  </div>
                  <div>
                    <p className="font-medium text-slate-900" data-testid={`document-name-${document.id}`}>
                      {document.originalName}
                    </p>
                    <p className="text-sm text-slate-500" data-testid={`document-size-${document.id}`}>
                      {formatFileSize(document.size)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  {getStatusBadge(document.status, document.errorMessage)}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteMutation.mutate(document.id)}
                    disabled={deleteMutation.isPending}
                    className="text-slate-400 hover:text-error"
                    data-testid={`button-delete-${document.id}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {(processingCount > 0 || !allProcessed) && (
            <div className="mt-6 p-4 bg-slate-100 rounded-lg" data-testid="processing-progress">
              <div className="flex items-center justify-between text-sm text-slate-600 mb-2">
                <span>Processing Documents</span>
                <span data-testid="progress-percentage">
                  {Math.round(progressPercentage)}%
                </span>
              </div>
              <Progress value={progressPercentage} className="h-2" data-testid="progress-bar" />
            </div>
          )}
          <div className="mt-6 flex justify-center">         
            <Button
              onClick={onProceedToQuery}
              disabled={!allProcessed || totalCount === 0}
              className="px-8 py-3 bg-primary text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="button-proceed-to-query"
            >
              PROCEED TO QUERY Sandip part
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
