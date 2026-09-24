import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory, search, ApiError } from "../api/client.js";
import { useToast } from "../lib/toast.jsx";
import { WorkspaceLayout } from "@/components/layout/WorkspaceLayout";

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function HistoryRow({ item }) {
  const confidence = (item.confidence * 100).toFixed(1);
  return (
    <div className="group border-b border-white/10 transition-colors hover:bg-white/5">
      <Link
        to={`/workspace?taskId=${item.task_id}`}
        className="flex flex-col lg:flex-row lg:items-center justify-between py-6 px-6 lg:px-[88px]"
      >
        <div className="flex flex-col lg:flex-row lg:items-center gap-6 lg:gap-16 flex-1">
          <div className="font-mono text-[9px] uppercase tracking-widest text-white/40 lg:w-24">
            {formatDate(item.created_at)}
          </div>
          <div className="flex-1 font-sans text-lg lg:text-xl font-light text-white line-clamp-1">
            {item.input_text || "Document Analysis"}
          </div>
        </div>

        <div className="flex items-center gap-12 mt-6 lg:mt-0">
          <div className="hidden lg:flex flex-col opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="font-mono text-[8px] uppercase tracking-widest text-white/40 mb-1">CONFIDENCE</span>
            <span className="font-mono text-xs text-white font-bold">{confidence}%</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="font-mono text-[8px] uppercase tracking-widest text-white/40 mb-1">CLASSIFICATION</span>
            <span className={`font-sans tracking-widest uppercase text-xs font-bold ${
              item.classification === "Likely Misleading" ? "text-red-400" : "text-white"
            }`}>
              {item.classification}
            </span>
          </div>
        </div>
      </Link>
    </div>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    document.title = "History | Rhea";
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await getHistory();
      setHistory(data);
    } catch (err) {
      if (err instanceof ApiError) {
        showToast(err.detail || "Failed to load history", "error");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) {
      fetchHistory();
      return;
    }
    setLoading(true);
    try {
      const data = await search(query);
      setHistory(data);
    } catch (err) {
      if (err instanceof ApiError) {
        showToast(err.detail || "Search failed", "error");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <WorkspaceLayout>
      <div className="flex-1 w-full flex flex-col relative overflow-hidden h-full min-h-[calc(100vh-80px)]">
        
        {/* Header Section */}
        <div className="w-full max-w-[1400px] mx-auto px-6 lg:px-[88px] pt-16 pb-12">
          <h1 className="font-sans font-light text-[clamp(4rem,7vw,8rem)] leading-[0.85] tracking-tight text-white mb-8 uppercase flex flex-col">
            <span className="font-serif italic capitalize text-[1.15em] font-normal leading-[0.7] pr-4 mb-2 text-white">The</span>
            <span className="font-semibold tracking-tighter text-white">ARCHIVE.</span>
          </h1>
          <p className="font-sans text-xl font-light text-white/60 max-w-xl">
            Historical records of previously mapped graph inferences.
          </p>
        </div>

        {/* Search & List Container */}
        <div className="w-full flex-1 flex flex-col bg-transparent relative z-10">
          
          {/* Search Header */}
          <div className="border-t border-b border-white/10 p-6 lg:px-[88px] lg:py-8 flex flex-col lg:flex-row gap-6 justify-between items-center max-w-[1400px] mx-auto w-full">
            <form onSubmit={handleSearch} className="w-full max-w-2xl flex items-center relative">
              <span className="absolute left-0 top-1/2 -translate-y-1/2 material-symbols-outlined text-white/40">
                search
              </span>
              <input
                type="text"
                placeholder="Search historical inferences by ID, classification, or text content..."
                className="w-full bg-transparent border-b border-white/20 focus:border-white py-4 pl-10 outline-none text-sm font-sans tracking-wide transition-colors placeholder:text-white/30 uppercase text-white"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button type="submit" className="hidden">Submit</button>
            </form>
            
            <div className="font-mono text-[9px] uppercase tracking-widest text-white/60 font-bold">
              {history.length} RECORD{history.length !== 1 ? 'S' : ''}
            </div>
          </div>

          {/* Results List */}
          <div className="flex-1 w-full max-w-[1400px] mx-auto flex flex-col pb-20">
            {loading ? (
              <div className="p-16 text-center font-mono text-xs uppercase tracking-widest text-white/40 animate-pulse">
                LOADING ARCHIVE...
              </div>
            ) : history.length === 0 ? (
              <div className="p-24 flex flex-col items-center justify-center text-center">
                 <div className="font-sans font-light text-3xl tracking-wide text-white/40 uppercase mb-4">NO RECORDS.</div>
                 <p className="font-mono text-[9px] uppercase tracking-[0.2em] font-medium text-white/30">
                   THE ARCHIVE CONTAINS NO STRUCTURAL MATCHES.
                 </p>
              </div>
            ) : (
              <div className="flex flex-col">
                {history.map((item) => (
                  <HistoryRow key={item.id} item={item} />
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </WorkspaceLayout>
  );
}
