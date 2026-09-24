import { motion } from "framer-motion";
import { Link } from "react-router-dom";

import SisyphusAscii from "../SisyphusAscii";

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

        {/* Right Visualization - Ascii Sisyphus */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 2, delay: 0.5 }}
          className="w-full lg:w-[50%] flex justify-center lg:justify-end absolute lg:relative top-0 right-0 h-full lg:h-[700px] -z-10 lg:z-20 opacity-30 lg:opacity-100"
        >
           <SisyphusAscii density={5} />
        </motion.div>
        
      </div>
    </section>
  );
}
