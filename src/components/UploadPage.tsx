import { useState, useRef } from "react";
import { FolderIcon, DocumentIcon } from "@heroicons/react/24/outline";

export default function UploadPage({ onProceed }: { onProceed: () => void }) {
  const [documents, setDocuments] = useState<Array<{ name: string; size: string; status: string }>>([
    { name: "research_paper_2025.pdf", size: "2.7 MB", status: "PROCESSED" },
    { name: "technical_report.docx", size: "1.8 MB", status: "PROCESSED" },
    { name: "meeting_notes.txt", size: "0.3 MB", status: "PROCESSING..." }
  ]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (files: FileList | null) => {
    if (!files) return;
    const newDocs = Array.from(files).map(f => ({
      name: f.name,
      size: `${(f.size / (1024 * 1024)).toFixed(1)} MB`,
      status: "PROCESSING..."
    }));
    setDocuments([...documents, ...newDocs]);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const processedDocs = documents.filter(doc => doc.status === "PROCESSED").length;
  const progressPercentage = Math.round((processedDocs / documents.length) * 100) || 0;

  return (
    <div className="w-full max-w-5xl mx-auto bg-white p-8">
      {/* Upload Area */}
      <div 
        className={`border-2 border-dashed ${isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300'} p-16 text-center rounded-lg mb-8`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="flex flex-col items-center">
          <div className="w-16 h-16 bg-gray-200 rounded-lg flex items-center justify-center mb-4">
            <FolderIcon className="w-8 h-8 text-gray-500" />
          </div>
          <p className="text-lg font-medium text-gray-700 mb-2">Drag and drop your documents here</p>
          <p className="text-sm text-gray-500 mb-4">or click to browse files</p>
          <p className="text-sm text-gray-400">Supported: PDF, DOCX, TXT | Max: 10MB per file | Limit: 10 files</p>
          <button className="mt-4 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded text-sm">
            Play & Drop Area
          </button>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={(e) => handleFileUpload(e.target.files)}
          className="hidden"
        />
      </div>

      {/* Uploaded Documents */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-medium text-gray-700">Uploaded Documents ({documents.length}/10)</h3>
          <span className="text-sm text-gray-500">Real-time Status</span>
        </div>
        
        <div className="space-y-3">
          {documents.map((doc, idx) => (
            <div key={idx} className="flex items-center justify-between bg-gray-50 p-3 rounded border">
              <div className="flex items-center gap-3">
                <DocumentIcon className="w-5 h-5 text-gray-500" />
                <div>
                  <span className="font-medium text-gray-800">{doc.name}</span>
                  <p className="text-xs text-gray-500">{doc.size}</p>
                </div>
              </div>
              <span className={`px-3 py-1 rounded text-xs font-medium ${
                doc.status === "PROCESSED" 
                  ? "bg-green-100 text-green-800" 
                  : "bg-yellow-100 text-yellow-800"
              }`}>
                {doc.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Progress Bar */}
      {documents.length > 0 && (
        <div className="mb-6">
          <div className="bg-gray-200 rounded-full h-6 relative overflow-hidden">
            <div 
              className="bg-gray-500 h-full transition-all duration-300 flex items-center justify-end pr-2"
              style={{ width: `${progressPercentage}%` }}
            >
              <span className="text-white text-xs font-medium">
                Processing Documents... {progressPercentage}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Proceed Button */}
      <div className="flex justify-center">
        <button 
          className={`px-8 py-3 rounded font-medium ${
            processedDocs === documents.length && documents.length > 0
              ? "bg-black text-white hover:bg-gray-800" 
              : "bg-gray-400 text-gray-600 cursor-not-allowed"
          }`}
          onClick={onProceed}
          disabled={!(processedDocs === documents.length && documents.length > 0)}
        >
          PROCEED TO QUERY
        </button>
      </div>
    </div>
  );
}
