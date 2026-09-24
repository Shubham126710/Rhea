import { motion } from "framer-motion";
import { Link } from "react-router-dom";

function HeroVisual() {
  return (
    <div className="w-full h-full relative overflow-hidden flex items-center justify-center opacity-80 mix-blend-screen pointer-events-none">
       {/* Background structural grid */}
       <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px]"></div>
       
       {/* Central Orbital System */}
       <div className="relative w-[500px] h-[500px] flex items-center justify-center">
         
         {/* Static geometric lines */}
         <div className="absolute w-[800px] h-px bg-white/10 rotate-45"></div>
         <div className="absolute w-[800px] h-px bg-white/10 -rotate-45"></div>
         <div className="absolute w-[800px] h-px bg-white/10"></div>
         <div className="absolute w-px h-[800px] bg-white/10"></div>
         
         {/* Concentric rings */}
         <motion.div 
           animate={{ rotate: 360 }} 
           transition={{ duration: 120, repeat: Infinity, ease: "linear" }}
           className="absolute w-[100%] h-[100%] border border-white/20 rounded-full border-dashed"
         ></motion.div>
         <motion.div 
           animate={{ rotate: -360 }} 
           transition={{ duration: 80, repeat: Infinity, ease: "linear" }}
           className="absolute w-[75%] h-[75%] border border-white/10 rounded-full"
         >
           <div className="absolute -top-1.5 left-1/2 w-3 h-3 bg-white/80 rounded-full shadow-[0_0_15px_rgba(255,255,255,0.5)]"></div>
         </motion.div>
         <motion.div 
           animate={{ rotate: 360 }} 
           transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
           className="absolute w-[40%] h-[40%] border border-white/30 rounded-full"
         >
           <div className="absolute top-1/4 -left-1 w-2 h-2 bg-white rounded-full"></div>
         </motion.div>
         
         {/* Connecting network nodes */}
         <svg className="absolute inset-0 w-full h-full overflow-visible" viewBox="0 0 500 500">
           <motion.path 
             initial={{ pathLength: 0, opacity: 0 }}
             animate={{ pathLength: 1, opacity: 0.3 }}
             transition={{ duration: 3, delay: 1, ease: "easeInOut" }}
             d="M 250 250 L 100 100 L 150 50 L 250 150 Z" 
             fill="none" 
             stroke="currentColor" 
             strokeWidth="1"
             className="text-white"
           />
           <motion.path 
             initial={{ pathLength: 0, opacity: 0 }}
             animate={{ pathLength: 1, opacity: 0.2 }}
             transition={{ duration: 4, delay: 1.5, ease: "easeInOut" }}
             d="M 250 250 L 400 350 L 450 200 L 250 100" 
             fill="none" 
             stroke="currentColor" 
             strokeWidth="1"
             className="text-white"
           />
         </svg>
         
         {/* Micro labels */}
         <div className="absolute top-10 left-10 font-mono text-[8px] text-white/40 tracking-widest uppercase">
           SYS.TOPOLOGY_01 <br/>
           COORD. 491.22
         </div>
         <div className="absolute bottom-20 right-10 font-mono text-[8px] text-white/40 tracking-widest uppercase text-right">
           SIGNAL PROPAGATION <br/>
           LATENCY: 12ms
         </div>
       </div>
    </div>
  );
}

export function Hero() {
  return (
    <section className="relative min-h-[100vh] bg-rhea-cobalt text-white pt-[88px] pb-10 flex flex-col justify-center overflow-hidden border-b border-white/20">
      
      {/* Texture */}
      <div className="absolute inset-0 bg-grain opacity-30 mix-blend-overlay pointer-events-none z-0"></div>
      
      <div className="max-w-[1600px] mx-auto w-full px-6 lg:px-[88px] relative z-10 flex flex-col lg:flex-row justify-between items-center gap-12 lg:gap-24 h-full flex-1">
        
        {/* Left Content */}
        <div className="w-full lg:w-[50%] flex flex-col justify-center z-20">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="font-sans text-[9px] uppercase tracking-[0.25em] font-medium text-white/60 mb-8 flex flex-col gap-2 border-l border-white/20 pl-6"
          >
            <span>RHEA / RESEARCH SYSTEM</span>
            <span>DUAL-LAYER GRAPH MODEL</span>
          </motion.div>
          
          <motion.h1 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.2, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="font-sans font-light text-[clamp(4rem,7vw,8rem)] leading-[0.85] tracking-tight text-white mb-8 uppercase flex flex-col"
          >
            <span className="font-semibold tracking-tighter text-white">WHERE</span>
            <span className="font-semibold tracking-tighter text-white/90">EVIDENCE</span>
            <span className="font-serif italic capitalize tracking-normal text-[1.15em] font-normal leading-[0.7] pr-4 mt-2 mb-2 text-white">Becomes</span>
            <span className="font-semibold tracking-tighter text-white">STRUCTURE.</span>
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.8 }}
            className="font-sans text-lg lg:text-xl font-light text-white/70 max-w-md leading-relaxed pl-2 mb-8"
          >
            Rhea models relationships surrounding information to detect patterns of structural propagation and misinformation.
          </motion.p>
          
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 1 }}
            className="flex flex-wrap items-center gap-6 pl-2"
          >
            <Link to="/login" className="bg-white text-rhea-cobalt hover:bg-white/90 font-sans text-[10px] uppercase tracking-[0.2em] font-semibold px-8 py-4 transition-colors">
              Get started
            </Link>
            <a href="/#method" className="text-white hover:text-white/70 font-sans text-[10px] uppercase tracking-[0.2em] font-medium px-8 py-4 transition-colors border border-white/20">
              View methodology
            </a>
          </motion.div>
        </div>

        {/* Right Visualization */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 2, delay: 0.5 }}
          className="w-full lg:w-[50%] flex justify-center lg:justify-end absolute lg:relative top-0 right-0 h-full lg:h-[700px] -z-10 lg:z-20 opacity-30 lg:opacity-100"
        >
           <HeroVisual />
        </motion.div>
        
      </div>
    </section>
  );
}
