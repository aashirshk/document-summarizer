import { useState, useEffect } from "react";
import { useSession } from "@/hooks/useSession";
import AppHeader from "@/components/AppHeader";
import DocumentUpload from "@/components/DocumentUpload";
import DocumentList from "@/components/DocumentList";
import SessionSidebar from "@/components/SessionSidebar";
import QueryInterface from "@/components/QueryInterface";

export default function DocumentSummarizer() {
  const { session, createSession, endSession } = useSession();
  const [showQueryInterface, setShowQueryInterface] = useState(false);

  useEffect(() => {
    // Create a new session when the component mounts
    createSession();
  }, [createSession]);

  const handleProceedToQuery = () => {
    setShowQueryInterface(true);
  };

  if (!session) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-slate-600">Starting new session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader session={session} onEndSession={endSession} />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <DocumentUpload sessionId={session.id} />
            <DocumentList 
              sessionId={session.id} 
              onProceedToQuery={handleProceedToQuery}
            />
          </div>
          
          <div className="space-y-6">
            <SessionSidebar session={session} />
          </div>
        </div>

        {showQueryInterface && (
          <QueryInterface sessionId={session.id} />
        )}
      </main>
    </div>
  );
}
