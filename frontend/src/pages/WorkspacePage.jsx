import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  submitText,
  submitUrl,
  submitFile,
  getResult,
  cancelAnalysis,
  pollStatus,
} from "../api/client.js";
import { WorkspaceLayout } from "@/components/layout/WorkspaceLayout";
import { useToast } from "../lib/toast.jsx";
import { cn } from "@/lib/utils";

export default function WorkspacePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const taskId = searchParams.get("taskId");

  const [inputType, setInputType] = useState("text"); 
  const [textInput, setTextInput] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [fileInput, setFileInput] = useState(null);

  const [loading, setLoading] = useState(false);
  const [canceling, setCanceling] = useState(false);
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  
  const { showToast } = useToast();
  const pollAbortController = useRef(null);

  useEffect(() => {
    document.title = "Workspace | Rhea";
    return () => {
      if (pollAbortController.current) {
        pollAbortController.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    if (taskId && !result) {
      startPolling(taskId);
    }
  }, [taskId]);

  const handleStartAnalysis = async () => {
    if (!textInput.trim() && inputType === "text") return;
    if (!urlInput.trim() && inputType === "url") return;
    if (!fileInput && inputType === "file") return;

    setLoading(true);
    setStatus("INITIALIZING...");
    setProgress(5);
    setResult(null);

    try {
      let data;
      if (inputType === "text") {
        data = await submitText(textInput);
      } else if (inputType === "url") {
        data = await submitUrl(urlInput);
      } else {
        data = await submitFile(fileInput);
      }
      setSearchParams({ taskId: data.task_id });
      startPolling(data.task_id);
    } catch (err) {
      showToast("Failed to start analysis", "error");
      setLoading(false);
    }
  };

  const startPolling = async (id) => {
    setLoading(true);
    if (pollAbortController.current) pollAbortController.current.abort();
    pollAbortController.current = new AbortController();
    const signal = pollAbortController.current.signal;

    try {
      await pollStatus(
        id,
        (currentStatus, currentProgress) => {
          setStatus(currentStatus.toUpperCase());
          setProgress(currentProgress);
        },
        signal
      );
      const res = await getResult(id, signal);
      setResult(res);
      showToast("Analysis complete", "success");
    } catch (err) {
      if (err.name !== "AbortError") {
        showToast(err.detail || "Analysis failed", "error");
      }
    } finally {
      if (signal.aborted) return;
      setLoading(false);
      pollAbortController.current = null;
    }
  };

  const handleCancel = async () => {
    if (!taskId) return;
    setCanceling(true);
    try {
      await cancelAnalysis(taskId);
      if (pollAbortController.current) {
        pollAbortController.current.abort();
      }
      setLoading(false);
      setSearchParams({});
      setStatus("CANCELLED");
      showToast("Analysis cancelled", "info");
    } catch (err) {
      showToast("Failed to cancel", "error");
    } finally {
      setCanceling(false);
    }
  };

  const resetWorkspace = () => {
    setResult(null);
    setSearchParams({});
    setTextInput("");
    setUrlInput("");
    setFileInput(null);
    setStatus("");
    setProgress(0);
  };

  return (
    <WorkspaceLayout>
      <div className="flex-1 w-full h-full min-h-[calc(100vh-80px)] flex flex-col relative overflow-hidden">
        
        <div className="flex-1 flex flex-col p-6 lg:px-[88px] lg:py-16 max-w-[1400px] mx-auto w-full">
          
          <AnimatePresence mode="wait">
            {!result && !loading && (
              <motion.div 
                key="input-view"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                className="flex-1 flex flex-col"
              >
                {/* Header */}
                <div className="mb-16">
                  <h1 className="font-sans font-light text-[clamp(4rem,7vw,8rem)] leading-[0.85] tracking-tight text-white mb-8 uppercase flex flex-col">
                    <span className="font-serif italic capitalize text-[1.15em] font-normal leading-[0.7] pr-4 mb-2 text-white">The</span>
                    <span className="font-semibold tracking-tighter text-white">WORKSPACE.</span>
                  </h1>
                  <p className="font-sans text-xl font-light text-white/60 max-w-xl">
                    Select a source and begin mapping the relationships beneath it.
                  </p>
                </div>

                <div className="w-full h-px bg-white/20 mb-8"></div>

                {/* Minimal Tabs */}
                <div className="flex gap-12 font-sans text-[10px] uppercase tracking-[0.2em] font-bold text-white/40 mb-10">
                  {["text", "url", "file"].map((type) => (
                    <button
                      key={type}
                      onClick={() => setInputType(type)}
                      className={cn(
                        "relative transition-colors hover:text-white pb-2",
                        inputType === type && "text-white"
                      )}
                    >
                      {type}
                      {inputType === type && (
                        <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-px bg-white" />
                      )}
                    </button>
                  ))}
                </div>

                {/* Input Field Area */}
                <div className="w-full flex-1 min-h-[300px] border border-white/20 p-8 lg:p-12 relative flex flex-col bg-white/5">
                  {inputType === "text" && (
                    <textarea
                      className="w-full flex-1 bg-transparent outline-none font-sans text-2xl lg:text-3xl font-light leading-relaxed text-white placeholder:text-white/20 resize-none"
                      placeholder="Enter claim or unstructured text..."
                      value={textInput}
                      onChange={(e) => setTextInput(e.target.value)}
                    />
                  )}
                  {inputType === "url" && (
                    <input
                      type="url"
                      className="w-full bg-transparent outline-none font-sans text-2xl lg:text-3xl font-light text-white placeholder:text-white/20"
                      placeholder="https://..."
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                    />
                  )}
                  {inputType === "file" && (
                    <div className="w-full flex-1 flex flex-col items-center justify-center gap-6 hover:bg-white/5 transition-colors cursor-pointer relative">
                      <input 
                        type="file" 
                        className="absolute inset-0 opacity-0 cursor-pointer"
                        onChange={(e) => setFileInput(e.target.files[0])}
                      />
                      <div className="font-serif italic text-4xl text-white/40">Upload</div>
                      <span className="font-sans text-[10px] uppercase tracking-[0.2em] font-medium text-white/50">
                        {fileInput ? fileInput.name : "Select a document"}
                      </span>
                    </div>
                  )}
                </div>

                {/* Action */}
                <div className="mt-8 flex justify-end">
                  <button
                    onClick={handleStartAnalysis}
                    className="font-sans text-[11px] uppercase tracking-[0.2em] font-bold text-white hover:opacity-70 transition-opacity flex items-center gap-4 group"
                  >
                    ANALYZE 
                    <span className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform">↗</span>
                  </button>
                </div>
              </motion.div>
            )}

            {loading && !result && (
              <motion.div 
                key="loading-view"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.8 }}
                className="flex-1 flex flex-col items-center justify-center w-full max-w-xl mx-auto text-center"
              >
                <div className="font-sans text-[10px] uppercase tracking-[0.2em] text-white font-bold mb-8 animate-pulse">
                   PROCESSING
                </div>
                
                <h2 className="font-serif italic font-normal text-6xl tracking-tight mb-16 text-white">
                  {status}
                </h2>
                
                <div className="w-full h-px bg-white/20 relative mb-8 overflow-hidden">
                   <motion.div 
                     className="absolute top-0 left-0 h-full bg-white" 
                     initial={{ width: 0 }}
                     animate={{ width: `${progress}%` }}
                     transition={{ duration: 0.5, ease: "easeOut" }}
                   ></motion.div>
                </div>
                
                <div className="w-full flex justify-between font-mono text-[9px] uppercase tracking-[0.2em] text-white/40 mb-16">
                   <span>SYS.GNN</span>
                   <span>{progress}%</span>
                </div>

                <button
                  onClick={handleCancel}
                  disabled={canceling}
                  className="font-sans text-[9px] uppercase tracking-[0.2em] font-bold text-white/40 hover:text-white transition-colors"
                >
                  {canceling ? "ABORTING..." : "CANCEL SEQUENCE ⨯"}
                </button>
              </motion.div>
            )}

            {result && (
              <motion.div 
                key="result-view"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
                className="flex flex-col w-full"
              >
                {/* Results Header */}
                <div className="flex justify-between items-end border-b border-white/20 pb-8 mb-16">
                  <div>
                    <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/50 block mb-4">
                      ANALYSIS COMPLETE // TASK ID: {taskId}
                    </span>
                    <h2 className="font-sans font-light text-[clamp(3rem,5vw,5rem)] leading-[0.9] tracking-tight uppercase flex flex-col">
                      <span className="font-serif italic capitalize text-[1.1em] font-normal leading-[0.7] pr-3 text-white">Structural</span>
                      <span className="font-semibold tracking-tighter text-white">SIGNAL.</span>
                    </h2>
                  </div>
                  <button 
                    onClick={resetWorkspace} 
                    className="font-sans text-[9px] uppercase tracking-[0.2em] font-bold text-white/50 hover:text-white transition-colors border-b border-white/20 pb-1"
                  >
                    NEW ANALYSIS ↺
                  </button>
                </div>
                
                {/* Results Canvas */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 lg:gap-24">
                  
                  {/* Left Column: Metrics & Explanation */}
                  <div className="lg:col-span-5 flex flex-col gap-16">
                     
                     <div>
                       <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/40 mb-6 border-b border-white/10 pb-2">01 — ASSESSMENT</div>
                       <div className="font-sans text-4xl lg:text-5xl font-light tracking-tight text-white mb-8 uppercase">
                         {result.classification}
                       </div>
                       <div className="flex gap-12 font-mono text-[9px] uppercase tracking-[0.2em] text-white/60">
                         <div>
                           <span className="block mb-2 text-white/40">CONFIDENCE</span>
                           <span className="text-white font-bold text-lg">{(result.confidence * 100).toFixed(1)}%</span>
                         </div>
                         <div>
                           <span className="block mb-2 text-white/40">COMPUTATION TIME</span>
                           <span className="text-white font-bold text-lg">1.24s</span>
                         </div>
                       </div>
                     </div>

                     <div>
                        <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/40 mb-6 border-b border-white/10 pb-2">02 — EXPLANATION</div>
                        <p className="font-sans text-base font-light leading-relaxed text-white/80">
                          {result.explanation || "No explanation provided for this result."}
                        </p>
                     </div>

                  </div>

                  {/* Right Column: Entities & Topology */}
                  <div className="lg:col-span-7 flex flex-col">
                    
                    <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/40 mb-6 border-b border-white/10 pb-2">03 — STRUCTURAL GRAPH</div>
                    
                    <div className="flex-1 min-h-[300px] border border-white/20 bg-white/5 relative flex flex-col p-8">
                       
                       <div className="flex justify-between font-mono text-[9px] uppercase tracking-[0.2em] text-white/50 mb-12">
                          <span>NODES: {result.metrics?.nodes || 0}</span>
                          <span>EDGES: {result.metrics?.edges || 0}</span>
                          <span>DENS: {result.metrics?.density?.toFixed(4) || 0.0}</span>
                       </div>

                       {/* Linear Functional Graph Representation */}
                       <div className="flex-1 flex flex-col items-center justify-center relative w-full px-8 py-16">
                          
                          <div className="flex items-center justify-between w-full relative z-10">
                            
                            <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.2 }} className="flex flex-col items-center gap-4">
                              <span className="font-sans text-xs uppercase tracking-widest text-white">ENTITY A</span>
                              <div className="w-2 h-2 rounded-full bg-white"></div>
                            </motion.div>

                            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 1 }} className="flex flex-col items-center gap-2">
                              <span className="font-mono text-[8px] uppercase tracking-[0.2em] text-white/60 bg-rhea-cobalt px-2 py-1">PROPAGATION RELATIONSHIP</span>
                            </motion.div>

                            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.6 }} className="flex flex-col items-center gap-4">
                              <span className="font-sans text-xs uppercase tracking-widest text-white">ENTITY B</span>
                              <div className="w-2 h-2 rounded-full bg-white"></div>
                            </motion.div>

                          </div>

                          {/* Connecting Line */}
                          <motion.div 
                            initial={{ width: 0 }} 
                            animate={{ width: "calc(100% - 4rem)" }} 
                            transition={{ duration: 1.5, delay: 0.5, ease: [0.22, 1, 0.36, 1] }} 
                            className="absolute top-1/2 left-8 h-[1px] bg-white/20 -translate-y-[calc(50%-1.25rem)] z-0"
                          ></motion.div>

                       </div>

                    </div>

                  </div>
                </div>

              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </div>
    </WorkspaceLayout>
  );
}
