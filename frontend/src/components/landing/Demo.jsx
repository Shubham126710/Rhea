import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

export function Demo() {
  const [input, setInput] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);

  const handleAnalyze = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    setAnalyzing(true);
    setResult(null);

    setTimeout(() => {
      setResult({
        entities: ["Climate change", "Extreme weather events"],
        relationships: "CAUSE → EFFECT",
        confidence: "87%",
        signal: "MODERATE",
      });
      setAnalyzing(false);
    }, 2000);
  };

  return (
    <section id="demo" className="bg-rhea-ivory text-rhea-black py-20 lg:py-32 px-6 lg:px-[88px] relative overflow-hidden border-b border-rhea-black/10 flex items-center">
      <div className="max-w-[1600px] mx-auto w-full relative z-10">
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 lg:gap-24">
          
          {/* Left Title */}
          <div className="lg:col-span-5 flex flex-col pt-10">
            <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-rhea-cobalt font-bold mb-12">03 — DEMONSTRATION</div>
            <h2 className="font-sans text-5xl lg:text-7xl font-light leading-[1.1] tracking-tight mb-8 uppercase">
              TEST THE <br/>
              <span className="font-serif italic capitalize text-[1.15em] text-rhea-cobalt pr-2 font-normal leading-[0.8]">System.</span>
            </h2>
            <p className="font-sans text-lg font-light leading-relaxed text-rhea-black/70 max-w-sm">
              Enter a claim and observe how Rhea maps its structural relationships.
            </p>
          </div>

          {/* Right Demo Console */}
          <div className="lg:col-span-7 flex flex-col justify-center">
            
            <div className="bg-white border border-rhea-black/20 p-8 lg:p-12 relative shadow-[0_20px_60px_-15px_rgba(0,0,0,0.05)] rounded-sm">
              
              <form onSubmit={handleAnalyze} className="flex flex-col gap-6">
                <label className="font-mono text-[9px] uppercase tracking-[0.25em] text-rhea-black/50 font-bold">
                  INPUT CLAIM
                </label>
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Climate change has increased the frequency of extreme weather events."
                  className="w-full bg-transparent border-b border-rhea-black/20 pb-4 outline-none focus:border-rhea-cobalt font-sans text-xl lg:text-2xl font-light transition-colors resize-none placeholder:text-rhea-black/20"
                  rows={2}
                />
                
                <AnimatePresence>
                  {!result && !analyzing && (
                    <motion.button
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      type="submit"
                      disabled={!input.trim()}
                      className="self-start mt-4 bg-rhea-black hover:bg-rhea-cobalt text-white font-sans text-[10px] uppercase tracking-[0.2em] font-medium px-8 py-4 transition-colors disabled:opacity-30"
                    >
                      RUN ANALYSIS →
                    </motion.button>
                  )}
                </AnimatePresence>
              </form>

              {/* Status and Results Area */}
              <div className="mt-12 pt-8 border-t border-rhea-black/10 min-h-[300px] flex flex-col relative">
                
                {!analyzing && !result && (
                  <div className="absolute inset-0 flex items-center justify-center opacity-30">
                    <span className="font-mono text-[9px] uppercase tracking-[0.2em]">Awaiting Input Sequence</span>
                  </div>
                )}
                
                {analyzing && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-6">
                    <div className="w-12 h-12 relative">
                      <div className="absolute inset-0 border border-rhea-black/10 rounded-full"></div>
                      <div className="absolute inset-0 border border-t-rhea-cobalt border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
                    </div>
                    <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-rhea-cobalt animate-pulse">ANALYZING STRUCTURE...</span>
                  </div>
                )}

                <AnimatePresence>
                  {result && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="w-full flex flex-col h-full"
                    >
                      <div className="flex justify-between items-center mb-10 pb-4 border-b border-rhea-black/10">
                        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-rhea-black/50 font-bold">
                          STATUS
                        </div>
                        <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-rhea-cobalt font-bold">
                          ANALYSIS COMPLETE
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                        
                        {/* Data Column */}
                        <div className="flex flex-col gap-8">
                          <div>
                            <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-rhea-black/40 mb-3">ENTITIES</div>
                            <div className="flex flex-col gap-1">
                              {result.entities.map(e => (
                                <div key={e} className="font-sans text-base text-rhea-black">{e}</div>
                              ))}
                            </div>
                          </div>
                          
                          <div>
                            <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-rhea-black/40 mb-3">RELATIONSHIPS</div>
                            <div className="font-sans text-base font-medium text-rhea-black">{result.relationships}</div>
                          </div>
                          
                          <div className="flex gap-12">
                            <div>
                              <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-rhea-black/40 mb-2">CONFIDENCE</div>
                              <div className="font-sans text-2xl font-light">{result.confidence}</div>
                            </div>
                            <div>
                              <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-rhea-black/40 mb-2">STRUCTURAL SIGNAL</div>
                              <div className="font-sans text-2xl font-light text-rhea-cobalt">{result.signal}</div>
                            </div>
                          </div>
                        </div>

                        {/* Graph Visualization Column */}
                        <div className="flex flex-col justify-center items-center bg-rhea-ivory/50 border border-rhea-black/10 p-6 relative overflow-hidden">
                           <div className="absolute top-4 left-4 font-mono text-[8px] uppercase tracking-[0.2em] text-rhea-black/30">TOPOLOGY MAP</div>
                           
                           {/* Mini interactive graph */}
                           <div className="relative w-full h-[180px] flex items-center justify-center mt-4">
                              {/* Edge */}
                              <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: "100%" }}
                                transition={{ duration: 1, delay: 0.5 }}
                                className="absolute top-1/2 left-0 h-px bg-rhea-cobalt/40 -translate-y-1/2 origin-left"
                              ></motion.div>
                              
                              {/* Left Node */}
                              <motion.div 
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ duration: 0.5 }}
                                className="absolute left-[10%] top-1/2 -translate-y-1/2 -translate-x-1/2 flex flex-col items-center gap-3 cursor-pointer group"
                              >
                                <div className="w-8 h-8 rounded-full bg-white border border-rhea-cobalt flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm z-10">
                                  <div className="w-2 h-2 rounded-full bg-rhea-cobalt"></div>
                                </div>
                                <span className="font-sans text-[10px] text-center max-w-[80px] leading-tight text-rhea-black/70">
                                  {result.entities[0]}
                                </span>
                              </motion.div>

                              {/* Right Node */}
                              <motion.div 
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ duration: 0.5, delay: 1 }}
                                className="absolute right-[10%] top-1/2 -translate-y-1/2 translate-x-1/2 flex flex-col items-center gap-3 cursor-pointer group"
                              >
                                <div className="w-8 h-8 rounded-full bg-white border border-rhea-black/30 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm z-10">
                                  <div className="w-1.5 h-1.5 rounded-full bg-rhea-black/50"></div>
                                </div>
                                <span className="font-sans text-[10px] text-center max-w-[80px] leading-tight text-rhea-black/70">
                                  {result.entities[1]}
                                </span>
                              </motion.div>
                              
                              {/* Relationship label */}
                              <motion.div 
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: 1.5 }}
                                className="absolute top-[35%] left-1/2 -translate-x-1/2 bg-white px-3 py-1 text-[8px] font-mono uppercase tracking-[0.2em] border border-rhea-black/10 text-rhea-cobalt rounded-sm z-20"
                              >
                                {result.relationships.split('→')[1]?.trim() || "CAUSE"}
                              </motion.div>
                           </div>
                        </div>

                      </div>
                      
                      <div className="mt-12 flex justify-end">
                        <button 
                          onClick={() => {
                            setResult(null);
                            setInput("");
                          }}
                          className="font-sans text-[9px] uppercase tracking-[0.2em] font-medium text-rhea-black/50 hover:text-rhea-black transition-colors flex items-center gap-2"
                        >
                          <span className="text-lg leading-none">↺</span> NEW ANALYSIS
                        </button>
                      </div>

                    </motion.div>
                  )}
                </AnimatePresence>
                
              </div>
              
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
