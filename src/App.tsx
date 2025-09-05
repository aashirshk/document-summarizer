import type { ReactElement } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import LandingPage from "./components/LandingPage";
import UploadPage from "./components/UploadPage";
import QueryPage from "./components/QueryPage";

function RequireIndexed({ children }: { children: ReactElement }) {
  // Frontend gate: set after successful processing
  const ok = sessionStorage.getItem("indexed") === "1";
  return ok ? children : <Navigate to="/upload" replace />;
}

function App() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route
          path="/query"
          element={
            <RequireIndexed>
              <QueryPage />
            </RequireIndexed>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
