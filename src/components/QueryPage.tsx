// import { useState } from "react";
// import Footer from "./Footer";

// export default function QueryPage() {
//   const [query, setQuery] = useState("");
//   const [response, setResponse] = useState("");

//   const handleGenerateResponse = () => {
//     setResponse(`
// Based on the uploaded documents, the findings indicate improvements in efficiency 
// with a 45% accuracy increase.

// "The implementation resulted in measurable performance gains across all test scenarios."
// Source: research_paper.pdf (p.12)

// Generated from 3 documents | 15 chunks | Processing time: 0.8s
//     `);
//   };

//   return (
//     <>
//     <div className="min-h-screen bg-gray-100 flex justify-center p-8">
//       <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-6xl">
        
//         {/* Query Section */}
//         <div className="bg-white shadow-md rounded-xl p-6">
//           <h2 className="text-lg font-semibold mb-3">Query Input</h2>
          
//           <textarea
//             className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-black focus:outline-none"
//             rows={5}
//             placeholder="Enter your question or request..."
//             value={query}
//             onChange={(e) => setQuery(e.target.value)}
//           />

//           {/* Option Buttons */}
//           <div className="flex gap-3 mt-4">
//             <button className="px-4 py-2 text-sm rounded-lg bg-blue-500 text-white hover:scale-105 hover:from-blue-700 hover:to-indigo-700 transition transform cursor-pointer">SUMMARY</button>
//             <button className="px-4 py-2 text-sm rounded-lg border  bg-blue-500 hover:scale-105 text-white hover:from-blue-700 hover:to-indigo-700 transition transform cursor-pointer">QUESTION</button>
//             <button className="px-4 py-2 text-sm rounded-lg border bg-blue-500 hover:scale-105 text-white hover:from-blue-700 hover:to-indigo-700 transition transform cursor-pointer">COMPARISON</button>
//           </div>

//           {/* Generate Button */}
//           <button
//             onClick={handleGenerateResponse}
//             className="w-full mt-5 py-3 rounded-lg bg-green-700 text-white font-medium hover:bg-green-500 transition"
//           >
//             GENERATE RESPONSE
//           </button>

//           {/* Recent Queries */}
//           <div className="mt-6">
//             <h3 className="text-md font-semibold mb-2">FAQs</h3>
//             <div className="space-y-2">
//               <button className="w-full text-left px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm">
//                 What are the main findings?
//               </button>
//               <button className="w-full text-left px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm">
//                 Compare methodologies used
//               </button>
//               <button className="w-full text-left px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm">
//                 Summarize conclusions
//               </button>
//             </div>
//           </div>
//         </div>

//         {/* Response Section */}
//         <div className="bg-white shadow-md rounded-xl p-6">
//           <h2 className="text-lg font-semibold mb-3">Response</h2>
//           <div className="border border-gray-200 bg-gray-50 rounded-lg p-4 min-h-[250px] whitespace-pre-line text-sm text-gray-800">
//             {response ? response : "Your response will appear here..."}
//           </div>
//         </div>

//       </div>
//     </div>
//     <Footer />
//     </>
//   );
// }

import { useEffect, useState, useRef } from "react";
import Footer from "./Footer";
import { API_BASE } from "../../utils/progress"; // same place you used in Upload page

type ApiResp = {
  answer: string;
  sources?: string[];
};

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  // summary states
  const [summary, setSummary] = useState<string>("");
  const [sumLoading, setSumLoading] = useState<boolean>(false);
  const [sumError, setSumError] = useState<string | null>(null);
  const [summaryOpen, setSummaryOpen] = useState<boolean>(true);

  // ---- helpers --------------------------------------------------------------

  const ranOnce = useRef(false);            // <-- guard
  const abortRef = useRef<AbortController | null>(null);

  async function askBackend(q: string, n = 3): Promise<string> {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const r = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, n_results: n }),
    });
    if (!r.ok) {
      const text = await r.text().catch(() => "");
      throw new Error(`Backend error ${r.status}: ${text || r.statusText}`);
    }
    const data: ApiResp = await r.json();
    return (data?.answer || "").trim();
  }

  // ---- auto-summary on mount -----------------------------------------------

  useEffect(() => {
    if (ranOnce.current) return;            // <-- prevents 2nd StrictMode run
    ranOnce.current = true;

    // Only attempt summary if we've actually indexed something in this session
    if (sessionStorage.getItem("indexed") !== "1") return;

    const run = async () => {
      try {
        setSumLoading(true);
        setSumError(null);

        // const q =
        //   "Give a brief, 5–8 bullet summary of the uploaded documents. " +
        //   "Focus on purpose, methods/approach, key findings, and limitations. " +
        //   "Keep bullets concise.";

        const q =  "Write a clear, cohesive paragraph-style summary (about 150–250 words) " +
        "of the uploaded documents. Explain the overall problem or goal, the " +
        "methods/approach used, the key results or findings, and any notable " +
        "limitations or implications. Use complete sentences and flowing prose. " +
        "Do not use bullet points or lists."

        const ans = await askBackend(q, 5);
        setSummary(ans || "No summary available.");
      } catch (err: any) {
        setSumError(err?.message || "Failed to load summary.");
      } finally {
        setSumLoading(false);
      }
    };

    run();
  }, []);

  // ---- user query -----------------------------------------------------------

  const handleGenerateResponse = async () => {
    if (!query.trim()) {
      setResponse("Please enter a question first.");
      return;
    }
    try {
      setLoading(true);
      const ans = await askBackend(query, 3);
      setResponse(ans || "No answer returned.");
    } catch (err: any) {
      setResponse(`Error: ${err?.message || "Failed to fetch response"}`);
    } finally {
      setLoading(false);
    }
  };

  const quickAsk = (q: string) => {
    setQuery(q);
    // (Optional) fire immediately:
    // handleGenerateResponse();
  };

  // ---- UI -------------------------------------------------------------------

  return (
    <>
      <div className="min-h-screen bg-gray-100 flex justify-center p-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-6xl">
          {/* Query Column */}
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
              <button
                onClick={() =>
                  quickAsk("Provide a concise summary of the key points and findings.")
                }
                className="px-4 py-2 text-sm rounded-lg bg-blue-500 text-white hover:scale-105 transition transform cursor-pointer"
              >
                SUMMARY
              </button>
              <button
                onClick={() =>
                  quickAsk("What are the main findings and their implications?")
                }
                className="px-4 py-2 text-sm rounded-lg bg-blue-500 text-white hover:scale-105 transition transform cursor-pointer"
              >
                QUESTION
              </button>
              <button
                onClick={() =>
                  quickAsk("Compare the methodologies used across the documents.")
                }
                className="px-4 py-2 text-sm rounded-lg bg-blue-500 text-white hover:scale-105 transition transform cursor-pointer"
              >
                COMPARISON
              </button>
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerateResponse}
              disabled={loading}
              className={`w-full mt-5 py-3 rounded-lg text-white font-medium transition ${
                loading ? "bg-green-400 cursor-wait" : "bg-green-700 hover:bg-green-600"
              }`}
            >
              {loading ? "Generating…" : "GENERATE RESPONSE"}
            </button>

            {/* FAQs */}
            <div className="mt-6">
              <h3 className="text-md font-semibold mb-2">FAQs</h3>
              <div className="space-y-2">
                <button
                  onClick={() => quickAsk("What are the main findings?")}
                  className="w-full text-left px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm"
                >
                  What are the main findings?
                </button>
                <button
                  onClick={() => quickAsk("Compare methodologies used")}
                  className="w-full text-left px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm"
                >
                  Compare methodologies used
                </button>
                <button
                  onClick={() => quickAsk("Summarize conclusions")}
                  className="w-full text-left px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm"
                >
                  Summarize conclusions
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Summary + Response */}
          <div className="space-y-6">
            {/* Auto Summary Card (collapsible) */}
            <div className="bg-white shadow-md rounded-xl p-6">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold">Document Summary</h2>
                <button
                  onClick={() => setSummaryOpen((s) => !s)}
                  className="text-sm text-blue-600 hover:underline"
                >
                  {summaryOpen ? "Hide" : "Show"}
                </button>
              </div>

              {summaryOpen && (
                <div className="border border-gray-200 bg-gray-50 rounded-lg p-4 min-h-[120px] whitespace-pre-line text-sm text-gray-800">
                  {sumLoading && "Generating summary…"}
                  {sumError && (
                    <div className="text-red-600">
                      {sumError} (try refreshing this page)
                    </div>
                  )}
                  {!sumLoading && !sumError && (summary || "No summary available.")}
                </div>
              )}
            </div>

            {/* Response Card */}
            <div className="bg-white shadow-md rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-3">Response</h2>
              <div className="border border-gray-200 bg-gray-50 rounded-lg p-4 min-h-[250px] whitespace-pre-line text-sm text-gray-800">
                {response ? response : "Your response will appear here..."}
              </div>
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}
