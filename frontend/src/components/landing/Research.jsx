import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function Research() {
  const flow = [
    "SOURCE",
    "ENTITY",
    "RELATIONSHIP",
    "PROPAGATION",
    "PATTERN"
  ];

  return (
    <section id="research" className="bg-rhea-ivory text-rhea-black py-32 lg:py-48 px-6 lg:px-[88px] relative overflow-hidden border-b border-rhea-black/10">
      
      <div className="max-w-[1600px] mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-16 lg:gap-24 relative z-10">
        
        {/* Left Side: Content & Metadata */}
        <div className="lg:col-span-5 flex flex-col pt-4">
          <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-rhea-cobalt font-bold mb-12">03 — RESEARCH</div>
          
          <h2 className="font-sans text-4xl lg:text-5xl font-light leading-snug tracking-tight mb-8">
            <span className="block font-semibold mb-2">THE PROBLEM</span>
            <span className="text-rhea-black/60 text-3xl lg:text-4xl">Information does not propagate randomly. It moves through relationships.</span>
          </h2>
          
          <div className="flex flex-col gap-6 font-sans text-lg font-light leading-relaxed text-rhea-black/80 max-w-md mb-16">
            <p>
              Traditional evaluation of digital information relies on semantic probability—analyzing the text in isolation. However, sophisticated misinformation networks construct elaborate, interconnected ecosystems to simulate credibility.
            </p>
            <p>
              Rhea approaches this topologically. By converting unstructured evidence into a mathematical structure, it exposes the underlying geometry of the information space, making invisible coordinated patterns visible.
            </p>
          </div>

          {/* Metadata Block */}
          <div className="flex flex-col gap-4 font-mono text-[9px] uppercase tracking-[0.2em] text-rhea-black/50 border-t border-rhea-black/10 pt-8 w-full max-w-sm">
             <div className="flex justify-between border-b border-rhea-black/10 pb-4">
               <span>SYSTEM</span>
               <span className="text-rhea-black font-semibold">RHEA / DUAL-LAYER GRAPH</span>
             </div>
             <div className="flex justify-between border-b border-rhea-black/10 pb-4">
               <span>DOMAIN</span>
               <span className="text-rhea-black font-semibold">INFORMATION STRUCTURE</span>
             </div>
             <div className="flex justify-between border-b border-rhea-black/10 pb-4">
               <span>MODEL</span>
               <span className="text-rhea-black font-semibold">RELATIONAL GRAPH</span>
             </div>
             <div className="flex justify-between pb-4">
               <span>OUTPUT</span>
               <span className="text-rhea-black font-semibold">STRUCTURAL EVIDENCE</span>
             </div>
          </div>
        </div>

        {/* Right Side: Visual Diagram */}
        <div className="lg:col-span-7 flex flex-col justify-center border-l border-rhea-black/10 pl-8 lg:pl-20 relative min-h-[500px]">
          
          <div className="absolute inset-0 opacity-5 pointer-events-none bg-[linear-gradient(to_right,rgba(0,0,0,1)_1px,transparent_1px),linear-gradient(to_bottom,rgba(0,0,0,1)_1px,transparent_1px)] bg-[size:40px_40px]"></div>

          <div className="flex flex-col relative z-10 w-full max-w-md mx-auto">
            {flow.map((step, idx) => (
              <motion.div 
                key={step}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.8, delay: idx * 0.15 }}
                className="flex items-center gap-8 group"
              >
                {/* Node & Line */}
                <div className="flex flex-col items-center">
                  <div className="w-4 h-4 border border-rhea-cobalt rounded-full flex items-center justify-center bg-rhea-ivory z-10 group-hover:scale-125 transition-transform duration-500">
                    <div className="w-1 h-1 bg-rhea-cobalt rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                  </div>
                  {idx !== flow.length - 1 && (
                    <div className="w-px h-16 lg:h-24 bg-rhea-black/15 group-hover:bg-rhea-cobalt/50 transition-colors duration-500"></div>
                  )}
                </div>
                
                {/* Text */}
                <div className={cn(
                  "font-sans text-2xl lg:text-3xl font-light tracking-wider transition-all duration-500",
                  idx !== flow.length - 1 ? "pb-16 lg:pb-24" : "",
                  "group-hover:text-rhea-cobalt"
                )}>
                  {step}
                </div>
              </motion.div>
            ))}
          </div>

        </div>
      </div>
    </section>
  );
}
