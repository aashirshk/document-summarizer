import { useState } from "react";

export default function UploadPage({ onProceed }: { onProceed: () => void }) {
  const [documents, setDocuments] = useState<Array<{ name: string; status: string }>>([]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setDocuments([...documents, ...files.map(f => ({ name: f.name, status: "Processed" }))]);
  };

  return (
    <div className="w-full max-w-3xl bg-white shadow-lg p-6 mt-12">
      <h2 className="text-xl font-semibold mb-4">Upload Documents</h2>
      <div className="border-2 border-dashed border-gray-400 p-10 text-center rounded">
        <input type="file" multiple onChange={handleFileUpload} />
        <p className="text-gray-500 mt-3">Supported: PDF, DOCX, TXT (Max 10MB each)</p>
      </div>

      <div className="mt-6">
        <h3 className="font-medium">Uploaded Documents ({documents.length}/10)</h3>
        <ul className="mt-2 space-y-2">
          {documents.map((doc, idx) => (
            <li key={idx} className="flex justify-between border p-2 rounded">
              <span>{doc.name}</span>
              <span className="text-green-600">{doc.status}</span>
            </li>
          ))}
        </ul>
      </div>

      <button 
        className={`mt-6 px-6 py-2 rounded ${documents.length === 0 ? "bg-gray-400 cursor-not-allowed" : "bg-black text-white hover:bg-gray-800"}`}
        onClick={onProceed}
        //disabled={documents.length === 0}
      >
        PROCEED TO QUERY
      </button>
    </div>
  );
}
