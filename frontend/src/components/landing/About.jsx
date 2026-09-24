export function About() {
  return (
    <section id="about" className="bg-rhea-ivory text-rhea-black py-32 lg:py-48 px-6 lg:px-[88px] relative overflow-hidden">
      <div className="max-w-[1600px] mx-auto w-full relative z-10 flex flex-col">
        
        {/* Top: Large Statement */}
        <div className="mb-24 lg:mb-32">
           <h2 className="font-sans text-5xl lg:text-[5.5rem] font-light leading-[0.95] tracking-tight text-rhea-black mb-12 uppercase max-w-5xl">
             <span className="block">Rhea is a system for</span>
             <span className="block font-semibold">understanding how</span>
             <span className="block text-rhea-cobalt font-semibold">
               <span className="font-serif italic capitalize text-[1.15em] font-normal tracking-normal pr-3">Information</span> 
               Moves.
             </span>
           </h2>
           <p className="font-sans text-xl lg:text-2xl font-light text-rhea-black/70 max-w-2xl leading-relaxed">
             A dual-layer graph neural network designed to extract, map, and analyze the relational geometry of claims to detect structural propagation.
           </p>
        </div>

        {/* Bottom: Three Blocks */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 lg:gap-16 border-t border-rhea-black/10 pt-16">
          
          <div className="flex flex-col group">
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-rhea-black/40 mb-6 flex items-center gap-4">
              01 <div className="h-px bg-rhea-black/10 flex-1 group-hover:bg-rhea-cobalt/50 transition-colors"></div>
            </div>
            <h3 className="font-sans text-2xl lg:text-3xl font-light tracking-tight mb-4 group-hover:text-rhea-cobalt transition-colors">EVIDENCE</h3>
            <p className="font-sans text-base font-light text-rhea-black/70 leading-relaxed pr-8">
              We examine information as connected structures rather than isolated claims.
            </p>
          </div>

          <div className="flex flex-col group">
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-rhea-black/40 mb-6 flex items-center gap-4">
              02 <div className="h-px bg-rhea-black/10 flex-1 group-hover:bg-rhea-cobalt/50 transition-colors"></div>
            </div>
            <h3 className="font-sans text-2xl lg:text-3xl font-light tracking-tight mb-4 group-hover:text-rhea-cobalt transition-colors">RELATIONSHIPS</h3>
            <p className="font-sans text-base font-light text-rhea-black/70 leading-relaxed pr-8">
              We model the entities and relationships surrounding information.
            </p>
          </div>

          <div className="flex flex-col group">
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-rhea-black/40 mb-6 flex items-center gap-4">
              03 <div className="h-px bg-rhea-black/10 flex-1 group-hover:bg-rhea-cobalt/50 transition-colors"></div>
            </div>
            <h3 className="font-sans text-2xl lg:text-3xl font-light tracking-tight mb-4 group-hover:text-rhea-cobalt transition-colors">PROPAGATION</h3>
            <p className="font-sans text-base font-light text-rhea-black/70 leading-relaxed pr-8">
              We surface how patterns travel through the network topology.
            </p>
          </div>

        </div>

      </div>
    </section>
  );
}
