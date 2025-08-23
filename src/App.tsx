import { useState } from "react";
import Navbar from "./components/Navbar";
import LandingPage from "./components/LandingPage";
import UploadPage from "./components/UploadPage";
import QueryPage from "./components/QueryPage";

function App() {
  const [page, setPage] = useState("landing");

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar onNavigate={setPage} />
      {page === "landing" && <LandingPage onStart={() => setPage("upload")} />}
      {page === "upload" && <UploadPage onProceed={() => setPage("query")} />}
      {page === "query" && <QueryPage />}
    </div>
  );
}

export default App;
