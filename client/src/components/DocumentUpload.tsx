import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { CloudUpload } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface DocumentUploadProps {
  sessionId: string;
}

export default function DocumentUpload({ sessionId }: DocumentUploadProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await apiRequest('POST', `/api/sessions/${sessionId}/documents`, formData);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/sessions', sessionId, 'documents'] });
      toast({
        title: "File uploaded successfully",
        description: "Document is being processed...",
      });
    },
    onError: (error) => {
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Failed to upload file",
        variant: "destructive",
      });
    },
  });

  const onDrop = useCallback((acceptedFiles: File[]) => {
    acceptedFiles.forEach((file) => {
      // Validate file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        toast({
          title: "File too large",
          description: "File size must be less than 10MB",
          variant: "destructive",
        });
        return;
      }

      // Validate file type
      const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
      ];

      if (!allowedTypes.includes(file.type)) {
        toast({
          title: "Invalid file type",
          description: "Only PDF, DOCX, and TXT files are allowed",
          variant: "destructive",
        });
        return;
      }

      uploadMutation.mutate(file);
    });
  }, [uploadMutation, toast]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    maxFiles: 10,
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6" data-testid="document-upload-section">
      <h2 className="text-lg font-semibold text-slate-900 mb-4" data-testid="upload-title">
        Document Upload
      </h2>
      
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-primary bg-blue-50'
            : 'border-slate-300 hover:border-primary hover:bg-blue-50'
        }`}
        data-testid="drop-zone"
      >
        <input {...getInputProps()} data-testid="file-input" />
        <div className="space-y-4">
          <div className="mx-auto w-16 h-16 bg-slate-100 rounded-lg flex items-center justify-center">
            <CloudUpload className="text-2xl text-slate-400" data-testid="upload-icon" />
          </div>
          <div>
            <p className="text-lg font-medium text-slate-700" data-testid="upload-primary-text">
              {isDragActive ? 'Drop the files here' : 'Drag and drop your documents here'}
            </p>
            <p className="text-sm text-slate-500 mt-1" data-testid="upload-secondary-text">
              or click to browse files
            </p>
          </div>
          <div className="text-xs text-slate-400" data-testid="upload-constraints">
            <p>Supported: PDF, DOCX, TXT | Max: 10MB per file | Limit: 10 files</p>
          </div>
        </div>
      </div>

      {uploadMutation.isPending && (
        <div className="mt-4 text-center" data-testid="upload-progress">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto mb-2"></div>
          <p className="text-sm text-slate-600">Uploading...</p>
        </div>
      )}
    </div>
  );
}
