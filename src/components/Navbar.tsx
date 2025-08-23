export default function Navbar({ onNavigate }: { onNavigate: (page: string) => void }) {
    return (
      <header className="w-full flex justify-between items-center bg-black text-white px-6 py-3">
        <h1 className="text-xl font-bold">DoCSuM</h1>
        <nav className="flex gap-6">
          <button onClick={() => onNavigate("landing")} className="hover:underline">Home</button>
          <button className="hover:underline">How It Works</button>
          <button className="hover:underline">Features</button>
          <button className="hover:underline">About</button>
          <button 
            className="bg-white text-black px-3 py-1 rounded hover:bg-gray-200"
            onClick={() => onNavigate("upload")}
          >
            Start Session
          </button>
        </nav>
      </header>
    );
  }