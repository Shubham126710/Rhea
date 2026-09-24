import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="bg-rhea-cobalt text-white relative overflow-hidden pt-32 pb-12 font-sans border-t border-white/20">
      {/* Texture */}
      <div className="absolute inset-0 bg-grain opacity-30 mix-blend-overlay pointer-events-none"></div>

      <div className="max-w-[1600px] mx-auto px-6 lg:px-[80px] relative z-10">
        
        {/* Main Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 lg:gap-8 mb-32 border-b border-white/20 pb-20">
          
          {/* Column 01: Brand Statement */}
          <div className="flex flex-col justify-start md:pr-12">
            <h3 className="font-serif italic font-normal text-5xl mb-6 tracking-wide pt-2">Rhea</h3>
            <p className="text-[13px] font-light leading-relaxed text-white/70">
              Research System.<br/>
              A dual-layer graph neural network mapping the structural propagation of information.
            </p>
          </div>
          
          {/* Column 02: Navigation */}
          <div className="flex flex-col gap-5 text-[11px] uppercase tracking-[0.2em] font-medium pt-2">
            <a href="/#research" className="hover:opacity-70 transition-opacity">Research</a>
            <a href="/#method" className="hover:opacity-70 transition-opacity">Method</a>
            <a href="/#demo" className="hover:opacity-70 transition-opacity">Demo</a>
            <a href="/#about" className="hover:opacity-70 transition-opacity">About</a>
          </div>
          
          {/* Column 03: Links */}
          <div className="flex flex-col gap-5 text-[11px] uppercase tracking-[0.2em] font-medium pt-2">
            <Link to="/workspace" className="hover:opacity-70 transition-opacity text-white">Enter Workspace ↗</Link>
            <a href="https://github.com/rhea-project" className="hover:opacity-70 transition-opacity text-white/70">GitHub</a>
            <a href="#" className="hover:opacity-70 transition-opacity text-white/70">Documentation</a>
            <a href="#" className="hover:opacity-70 transition-opacity text-white/70">API</a>
          </div>
          
          {/* Column 04: Metadata */}
          <div className="flex flex-col gap-5 text-[11px] uppercase tracking-[0.2em] font-medium pt-2 text-white/50 font-mono">
            <div>SYS.VER // 1.0.0</div>
            <div>STATUS // ACTIVE</div>
            <div>ENV // PRODUCTION</div>
            <div>NODE // US-EAST-1</div>
          </div>
          
        </div>

        {/* Bottom Row */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 font-sans text-[10px] uppercase tracking-[0.2em] font-medium text-white/60">
          <div className="flex items-center gap-6">
            <span>© 2026 RHEA</span>
            <span className="hidden sm:inline">MIT LICENSE</span>
          </div>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:opacity-100 transition-opacity">TERMS</a>
            <a href="#" className="hover:opacity-100 transition-opacity">PRIVACY</a>
          </div>
        </div>
        
      </div>
    </footer>
  );
}
