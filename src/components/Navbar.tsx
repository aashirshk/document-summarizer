export default function Navbar({ onNavigate }: { onNavigate: (page: string) => void }) {
    return (
      <header className="w-full flex justify-between items-center bg-gray-800 text-white px-6 py-2">
        <div className="flex items-center">
          <span className="text-sm bg-gray-700 px-2 py-1 rounded mr-4">SCREEN 02 - DOCUMENT UPLOAD</span>
        </div>
        <h1 className="text-lg font-bold tracking-wide">TEXT SUMMARIZER</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm">SESSION: 26 56 REMAINING</span>
          <button 
            className="bg-gray-600 hover:bg-gray-500 px-3 py-1 rounded text-sm"
            onClick={() => onNavigate("landing")}
          >
            END SESSION
          </button>
        </div>
      </header>
    );
  }