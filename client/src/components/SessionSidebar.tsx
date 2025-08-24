import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Wand2, Download, Trash2 } from "lucide-react";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import type { Session } from "@shared/schema";

interface SessionSidebarProps {
  session: Session;
}

interface OllamaHealth {
  status: string;
  model?: string;
}

export default function SessionSidebar({ session }: SessionSidebarProps) {
  const { toast } = useToast();

  const { data: ollamaHealth } = useQuery<OllamaHealth>({
    queryKey: ['/api/ollama/health'],
    refetchInterval: 30000, // Check every 30 seconds
  });


  const summarizeMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest('POST', `/api/sessions/${session.id}/summarize`);
      return response.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Summary generated",
        description: "Auto-summary has been generated successfully",
      });
      // You might want to display the summary in a modal or separate component
      console.log('Summary:', data.summary);
    },
    onError: (error) => {
      toast({
        title: "Summary failed",
        description: error instanceof Error ? error.message : "Failed to generate summary",
        variant: "destructive",
      });
    },
  });


  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(3)) + ' ' + sizes[i];
  };

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  return (
    <div className="space-y-6">
      {/* Session Info */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6" data-testid="session-info">
        <h3 className="text-lg font-semibold text-slate-900 mb-4" data-testid="session-info-title">
          Session Information
        </h3>
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-slate-600">Session ID</span>
            <span className="text-sm font-mono text-slate-900" data-testid="session-id">
              #{session.id.slice(-8).toUpperCase()}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-slate-600">Started</span>
            <span className="text-sm text-slate-900" data-testid="session-start-time">
              {formatTime(session.startTime)}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-slate-600">Documents</span>
            <span className="text-sm text-slate-900" data-testid="session-document-count">
              {session.documentCount} files
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-slate-600">Total Size</span>
            <span className="text-sm text-slate-900" data-testid="session-total-size">
              {formatFileSize(session.totalSize)}
            </span>
          </div>
        </div>
      </div>


      {/* LLM Status */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6" data-testid="ollama-status">
        <h3 className="text-lg font-semibold text-slate-900 mb-4" data-testid="ollama-status-title">
          Ollama Status
        </h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">Model</span>
            <Badge
              variant={ollamaHealth?.status === 'connected' ? 'default' : 'secondary'}
              className={ollamaHealth?.status === 'connected' ? 'bg-green-100 text-green-800' : ''}
              data-testid="model-status"
            >
              <div className={`w-2 h-2 rounded-full mr-2 ${
                ollamaHealth?.status === 'connected' ? 'bg-green-400' : 'bg-slate-400'
              }`}></div>
              {ollamaHealth?.model || 'Llama 3'}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">Connection</span>
            <Badge
              variant={ollamaHealth?.status === 'connected' ? 'default' : 'secondary'}
              className={ollamaHealth?.status === 'connected' ? 'bg-green-100 text-green-800' : ''}
              data-testid="connection-status"
            >
              <div className={`w-2 h-2 rounded-full mr-2 ${
                ollamaHealth?.status === 'connected' ? 'bg-green-400' : 'bg-slate-400'
              }`}></div>
              {ollamaHealth?.status === 'connected' ? 'Connected' : 'Disconnected'}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-600">Response Time</span>
            <span className="text-sm text-slate-900" data-testid="response-time">
              ~2.3s
            </span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6" data-testid="quick-actions">
        <h3 className="text-lg font-semibold text-slate-900 mb-4" data-testid="quick-actions-title">
          Quick Actions
        </h3>
        <div className="space-y-3">
          <Button
            onClick={() => summarizeMutation.mutate()}
            disabled={summarizeMutation.isPending || session.documentCount === 0}
            className="w-full bg-slate-100 text-slate-700 hover:bg-slate-200"
            variant="outline"
            data-testid="button-generate-summary"
          >
            <Wand2 className="w-4 h-4 mr-2" />
            Auto-Generate Summary
          </Button>
          <Button
            className="w-full bg-slate-100 text-slate-700 hover:bg-slate-200"
            variant="outline"
            data-testid="button-export-session"
          >
            <Download className="w-4 h-4 mr-2" />
            Export Session Data
          </Button>
          <Button
            className="w-full bg-red-50 text-red-700 hover:bg-red-100"
            variant="outline"
            data-testid="button-clear-session"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear Session
          </Button>
        </div>
      </div>
    </div>
  );
}
