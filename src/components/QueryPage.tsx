import { useState } from "react";

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");

  const handleGenerateResponse = () => {
    setResponse("Based on the uploaded documents, the findings indicate improvements in efficiency with a 45% accuracy increase.");
  };

  return (
    <div className="w-full max-w-5xl bg-white shadow-lg p-6 mt-12 grid grid-cols-2 gap-6">
      {/* Query Section */}
      <div>
        <h2 className="text-lg font-semibold">Query Input</h2>
        <textarea 
          className="w-full border p-2 rounded mt-2"
          rows={4}
          placeholder="Enter your question or request..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="flex gap-2 mt-3">
          <button className="border px-3 py-1 rounded hover:bg-gray-100">Summary</button>
          <button className="border px-3 py-1 rounded hover:bg-gray-100">Question</button>
          <button className="border px-3 py-1 rounded hover:bg-gray-100">Comparison</button>
        </div>
        <button 
          className="mt-4 bg-black text-white px-4 py-2 rounded hover:bg-gray-800"
          onClick={handleGenerateResponse}
        >
          GENERATE RESPONSE
        </button>

        <div className="mt-6">
          <h3 className="font-medium">Recent Queries</h3>
          <ul className="list-disc ml-6 text-gray-600 mt-2">
            <li>What are the main findings?</li>
            <li>Compare methodologies used</li>
            <li>Summarize conclusions</li>
          </ul>
        </div>
      </div>

      {/* Response Section */}
      <div>
        <h2 className="text-lg font-semibold">Response</h2>
        <div className="border p-4 mt-2 rounded bg-gray-50 min-h-[200px]">
          {response ? response : "Generated response will appear here..."}
        </div>
      </div>
    </div>
  );
}
