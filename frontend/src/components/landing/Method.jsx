import { useRef, useEffect, useState } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { cn } from "@/lib/utils";

const stages = [
  {
    num: "01",
    title: "INGEST",
    desc: "Extract unstructured information and metadata.",
  },
  {
    num: "02",
    title: "REPRESENT",
    desc: "Convert language and evidence into computational representations.",
  },
  {
    num: "03",
    title: "CONNECT",
    desc: "Identify relationships between entities, claims and sources.",
  },
  {
    num: "04",
    title: "ANALYZE",
    desc: "Detect patterns, contradictions and structural relationships.",
  },
  {
    num: "05",
    title: "SURFACE",
    desc: "Present evidence and relationships in an interpretable form.",
  }
];

export function Method() {
  const containerRef = useRef(null);
  const [activeIndex, setActiveIndex] = useState(0);
  
  // The method section is a sticky scroll sequence
  // We make it 500vh tall and use framer-motion to track scroll progress
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  useEffect(() => {
    return scrollYProgress.onChange((latest) => {
      // Map 0-1 to 0-4
      const index = Math.min(Math.floor(latest * 5), 4);
      setActiveIndex(index);
    });
  }, [scrollYProgress]);

  return (
    <section 
      id="method" 
      ref={containerRef}
      className="bg-rhea-cobalt text-white relative h-[500vh]"
    >
      <div className="sticky top-0 h-screen w-full overflow-hidden flex items-center justify-center">
        {/* Texture */}
        <div className="absolute inset-0 bg-grain opacity-30 mix-blend-overlay pointer-events-none z-0"></div>
        
        {/* Large Ghost Number indicating current step */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[40vw] font-sans font-medium text-white/5 tracking-tighter leading-none pointer-events-none transition-all duration-1000 select-none">
          {stages[activeIndex].num}
        </div>

        <div className="max-w-[1600px] mx-auto w-full px-6 lg:px-[80px] relative z-10 grid grid-cols-1 md:grid-cols-2 gap-12">
           
           {/* Static Left Side (Index list) */}
           <div className="flex flex-col justify-center gap-6 border-l border-white/20 pl-8 lg:pl-16 relative">
             <div className="font-mono text-xs text-white/50 font-bold mb-12 absolute -top-20 left-8">02 — METHODOLOGY</div>
             
             {stages.map((stage, idx) => (
               <div 
                 key={stage.num}
                 className={cn(
                   "flex items-center gap-8 transition-all duration-500",
                   idx === activeIndex ? "opacity-100 translate-x-4" : "opacity-30 translate-x-0"
                 )}
               >
                 <span className="font-sans text-3xl lg:text-5xl font-light tracking-tight">{stage.title}</span>
               </div>
             ))}
           </div>

           {/* Dynamic Right Side (Content for active stage) */}
           <div className="flex flex-col justify-center h-full relative">
             {stages.map((stage, idx) => (
               <div
                 key={`content-${stage.num}`}
                 className={cn(
                   "absolute top-1/2 left-0 -translate-y-1/2 w-full transition-all duration-700 ease-[cubic-bezier(0.22,1,0.36,1)]",
                   idx === activeIndex 
                     ? "opacity-100 translate-y-0" 
                     : idx < activeIndex 
                       ? "opacity-0 -translate-y-12" 
                       : "opacity-0 translate-y-12"
                 )}
               >
                 <div className="font-display italic text-6xl lg:text-8xl text-white/90 mb-8 leading-[0.8]">
                   {stage.num}
                 </div>
                 <div className="h-px w-24 bg-white/30 mb-8"></div>
                 <p className="font-sans text-xl lg:text-3xl font-light leading-relaxed max-w-xl text-white/80">
                   {stage.desc}
                 </p>
               </div>
             ))}
           </div>
           
        </div>
      </div>
    </section>
  );
}
