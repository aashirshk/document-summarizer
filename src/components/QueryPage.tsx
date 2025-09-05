import { useState } from "react";
import Footer from "./Footer";

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");

  const handleGenerateResponse = () => {
    setResponse(`
Based on the uploaded documents, the findings indicate improvements in efficiency 
with a 45% accuracy increase.

"The implementation resulted in measurable performance gains across all test scenarios."
Source: research_paper.pdf (p.12)

Generated from 3 documents | 15 chunks | Processing time: 0.8s
    `);
  };

  return (
    <>
    <div className="min-h-screen bg-gray-100 flex justify-center p-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-6xl">
        
        {/* Query Section */}
        <div className="bg-white shadow-md rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-3">Query Input</h2>
          
          <textarea
            className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-black focus:outline-none"
            rows={5}
            placeholder="Enter your question or request..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          {/* Option Buttons */}
          <div className="flex gap-3 mt-4">
            <button className="px-4 py-2 text-sm rounded-lg bg-blue-500 text-white hover:scale-105 hover:from-blue-700 hover:to-indigo-700 transition transform cursor-pointer">SUMMARY</button>
            <button className="px-4 py-2 text-sm rounded-lg border  bg-blue-500 hover:scale-105 text-white hover:from-blue-700 hover:to-indigo-700 transition transform cursor-pointer">QUESTION</button>
            <button className="px-4 py-2 text-sm rounded-lg border bg-blue-500 hover:scale-105 text-white hover:from-blue-700 hover:to-indigo-700 transition transform cursor-pointer">COMPARISON</button>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerateResponse}
            className="w-full mt-5 py-3 rounded-lg bg-green-700 text-white font-medium hover:bg-green-500 transition"
          >
            GENERATE RESPONSE
          </button>

          {/* Recent Queries */}
          <div className="mt-6">
            <h3 className="text-md font-semibold mb-2">FAQs</h3>
            <div className="space-y-2">
              <button className="w-full text-left px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm">
                What are the main findings?
              </button>
              <button className="w-full text-left px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm">
                Compare methodologies used
              </button>
              <button className="w-full text-left px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm">
                Summarize conclusions
              </button>
            </div>
          </div>
        </div>

        {/* Response Section */}
        <div className="bg-white shadow-md rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-3">Response</h2>
          <div className="border border-gray-200 bg-gray-50 rounded-lg p-4 min-h-[250px] whitespace-pre-line text-sm text-gray-800">
            {response ? response : "Your response will appear here..."}
          </div>
        </div>

      </div>
    </div>
    <Footer />
    </>
  );
}
