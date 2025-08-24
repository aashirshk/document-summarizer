import { useState, useCallback } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import type { Session } from "@shared/schema";

export function useSession() {
  const { toast } = useToast();
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  const { data: session, isLoading } = useQuery<Session>({
    queryKey: ['/api/sessions', currentSessionId],
    enabled: !!currentSessionId,
    refetchInterval: 10000, // Refetch every 10 seconds to update counts
  });

  const createSessionMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest('POST', '/api/sessions', {});
      return response.json() as Promise<Session>;
    },
    onSuccess: (newSession) => {
      setCurrentSessionId(newSession.id);
      toast({
        title: "Session started",
        description: "New document processing session has been created",
      });
    },
    onError: (error) => {
      toast({
        title: "Failed to start session",
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    },
  });

  const endSessionMutation = useMutation({
    mutationFn: async (sessionId: string) => {
      const response = await apiRequest('POST', `/api/sessions/${sessionId}/end`);
      return response.json() as Promise<Session>;
    },
    onSuccess: () => {
      setCurrentSessionId(null);
      toast({
        title: "Session ended",
        description: "Document processing session has been terminated",
      });
    },
    onError: (error) => {
      toast({
        title: "Failed to end session",
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    },
  });

  const createSession = useCallback(() => {
    if (!createSessionMutation.isPending && !currentSessionId) {
      createSessionMutation.mutate();
    }
  }, [createSessionMutation, currentSessionId]);

  const endSession = useCallback(() => {
    if (currentSessionId && !endSessionMutation.isPending) {
      endSessionMutation.mutate(currentSessionId);
    }
  }, [currentSessionId, endSessionMutation]);

  return {
    session,
    isLoading: isLoading || createSessionMutation.isPending,
    createSession,
    endSession,
  };
}
