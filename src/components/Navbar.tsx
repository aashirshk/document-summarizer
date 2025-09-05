// src/components/Navbar.tsx
import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="max-w-6xl mx-auto h-14 px-5 flex items-center">
        <Link to="/" className="text-xl font-extrabold text-slate-900">
          DoCSuM
        </Link>
        {/* keep any marketing links if you want; omit upload/query */}
        <div className="ml-auto flex items-center gap-4">
          <a className="text-slate-600 hover:text-slate-900" href="#how">How It Works</a>
          <a className="text-slate-600 hover:text-slate-900" href="#features">Features</a>
          <Link
            to="/upload"
            className="rounded-md bg-blue-600 px-3 py-1.5 text-white font-semibold"
          >
            Start Session
          </Link>
        </div>
      </div>
    </nav>
  );
}
