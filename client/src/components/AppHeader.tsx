import { useState, useEffect } from "react";
import { FileText, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Session } from "@shared/schema";

interface AppHeaderProps {
  session: Session;
  onEndSession: () => void;
}

export default function AppHeader({ session, onEndSession }: AppHeaderProps) {
  const [remainingTime, setRemainingTime] = useState(30 * 60); // 30 minutes in seconds

  useEffect(() => {
    const timer = setInterval(() => {
      setRemainingTime(prev => {
        if (prev <= 0) {
          onEndSession();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [onEndSession]);

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')} REMAINING`;
  };

  return (
    <header className="bg-white border-b border-slate-200 shadow-sm" data-testid="app-header">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <FileText className="text-primary text-xl" data-testid="app-logo" />
              <h1 className="text-xl font-semibold text-slate-900" data-testid="app-title">
                Context Aware Document Summarizer
              </h1>
            </div>
            <Badge variant="secondary" className="hidden sm:inline-flex bg-blue-100 text-blue-800" data-testid="app-badge">
              Powered by Ollama Llama 3
            </Badge>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-sm text-slate-600" data-testid="session-timer">
              <Clock className="w-4 h-4" />
              <span className="font-mono" data-testid="timer-display">
                {formatTime(remainingTime)}
              </span>
            </div>
            <Button 
              onClick={onEndSession}
              variant="outline"
              className="bg-slate-600 text-white hover:bg-slate-700"
              data-testid="button-end-session"
            >
              END SESSION
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
