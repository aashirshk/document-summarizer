import {
  RocketLaunchIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  Cog6ToothIcon,
  MagnifyingGlassIcon,
  UserGroupIcon,
} from "@heroicons/react/24/solid";
import Footer from "./Footer";

export default function LandingPage({ onStart }: { onStart: () => void }) {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center text-center py-20 bg-white px-6">
        <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 mb-6 max-w-3xl">
          Context-Aware Document Summarizer
        </h1>
        <p className="text-lg text-gray-600 mb-10 max-w-2xl">
          Summarize, Compare, and Analyze Multiple Documents with AI-powered
          Retrieval-Augmented Generation (RAG) and Large Language Models (LLMs).
        </p>
        <button
          onClick={onStart}
          className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 
                     text-white px-8 py-3 rounded-lg shadow-lg hover:scale-105 
                     hover:from-blue-700 hover:to-indigo-700 transition transform cursor-pointer"
        >
          <RocketLaunchIcon className="h-6 w-6 text-white" />
          Start Session
        </button>
      </section>

      {/* Features Section */}
      <section className="bg-gray-50 py-20 flex-1 w-full">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-10 px-6 text-center">
          {/* Feature 1 */}
          <div className="bg-white p-8 shadow-md rounded-2xl hover:-translate-y-2 hover:shadow-xl transition">
            <DocumentTextIcon className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">Multi-Document RAG</h3>
            <p className="text-gray-600 text-sm">
              Process multiple documents with Cohere reranking for improved accuracy.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="bg-white p-8 shadow-md rounded-2xl hover:-translate-y-2 hover:shadow-xl transition">
            <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">Contradiction Detection</h3>
            <p className="text-gray-600 text-sm">
              Identify and highlight conflicting information between documents.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="bg-white p-8 shadow-md rounded-2xl hover:-translate-y-2 hover:shadow-xl transition">
            <Cog6ToothIcon className="h-12 w-12 text-green-600 mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">Adaptive Personalization</h3>
            <p className="text-gray-600 text-sm">
              System adapts to your preferences, workflows, and usage patterns.
            </p>
          </div>

          {/* Feature 4 */}
          <div className="bg-white p-8 shadow-md rounded-2xl hover:-translate-y-2 hover:shadow-xl transition">
            <MagnifyingGlassIcon className="h-12 w-12 text-purple-600 mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">Context-Aware Summaries</h3>
            <p className="text-gray-600 text-sm">
              Generate summaries tailored to document type and user roles.
            </p>
          </div>

          {/* Feature 5 */}
          <div className="bg-white p-8 shadow-md rounded-2xl hover:-translate-y-2 hover:shadow-xl transition">
            <UserGroupIcon className="h-12 w-12 text-orange-500 mx-auto mb-4" />
            <h3 className="font-semibold text-lg mb-2">Role-Based Adaptation</h3>
            <p className="text-gray-600 text-sm">
              Executives, Researchers, Students, or Analysts — get insights your way.
            </p>
          </div>
        </div>
      </section>

      {/* Trusted Use Cases Section */}
      <section className="py-16 bg-white text-center w-full">
        <h2 className="text-2xl font-bold mb-8 text-gray-900">Trusted Across Domains</h2>
        <div className="flex flex-wrap justify-center gap-6 max-w-4xl mx-auto">
          <div className="bg-gray-100 px-6 py-4 rounded-xl shadow hover:shadow-md transition">
            📚 Academic Research
          </div>
          <div className="bg-gray-100 px-6 py-4 rounded-xl shadow hover:shadow-md transition">
            ⚖️ Legal Professionals
          </div>
          <div className="bg-gray-100 px-6 py-4 rounded-xl shadow hover:shadow-md transition">
            🏥 Healthcare Analysis
          </div>
          <div className="bg-gray-100 px-6 py-4 rounded-xl shadow hover:shadow-md transition">
            💼 Business Insights
          </div>
        </div>
      </section>

      {/* Footer */}
      <Footer />
    </div>
  );
}
