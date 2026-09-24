import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

export function WorkspaceLayout({ children }) {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-rhea-cobalt text-white font-sans selection:bg-white selection:text-rhea-cobalt flex flex-col relative">
      <div className="fixed inset-0 bg-grain opacity-30 mix-blend-overlay pointer-events-none z-0"></div>
      
      {/* Workspace Header - Fixed and Consistent */}
      <header className="fixed top-0 left-0 right-0 w-full flex items-center justify-between px-6 lg:px-[88px] h-[72px] lg:h-[88px] z-50 bg-rhea-cobalt/95 backdrop-blur-sm border-b border-white/10">
        
        {/* Left Links (Desktop) / Spacer (Mobile) */}
        <div className="flex-1 flex justify-start gap-8 lg:gap-12 font-sans text-[10px] uppercase tracking-[0.2em] font-medium">
          <div className="hidden md:flex gap-8 lg:gap-12">
            <Link 
              to="/workspace" 
              className={cn(
                "hover:text-white transition-colors relative py-2",
                location.pathname === "/workspace" ? "text-white" : "text-white/50"
              )}
            >
              Workspace
              {location.pathname === "/workspace" && <div className="absolute bottom-0 left-0 right-0 h-px bg-white"></div>}
            </Link>
            <Link 
              to="/search" 
              className={cn(
                "hover:text-white transition-colors relative py-2",
                location.pathname === "/search" ? "text-white" : "text-white/50"
              )}
            >
              History
              {location.pathname === "/search" && <div className="absolute bottom-0 left-0 right-0 h-px bg-white"></div>}
            </Link>
          </div>
        </div>

        {/* Center Logo - Mathematically Centered */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
          <Link to="/" className="font-serif italic font-normal text-3xl lg:text-[2.5rem] tracking-wide hover:opacity-70 transition-opacity leading-none pt-1">
            Rhea
          </Link>
        </div>

        {/* Right Links (Desktop) / Hamburger (Mobile) */}
        <div className="flex-1 flex justify-end gap-8 lg:gap-12 font-sans text-[10px] uppercase tracking-[0.2em] font-medium">
          <div className="hidden md:flex gap-8 lg:gap-12">
            <Link 
              to="/settings" 
              className={cn(
                "hover:text-white transition-colors relative py-2",
                location.pathname === "/settings" ? "text-white" : "text-white/50"
              )}
            >
              Settings
              {location.pathname === "/settings" && <div className="absolute bottom-0 left-0 right-0 h-px bg-white"></div>}
            </Link>
            <Link to="/" className="text-white/50 hover:text-white transition-colors py-2">
              Exit ↗
            </Link>
          </div>

          <button 
            className="md:hidden flex flex-col gap-1.5 p-2 z-50 group"
            onClick={() => setMenuOpen(true)}
          >
            <div className="w-6 h-[1px] bg-white transition-all"></div>
            <div className="w-6 h-[1px] bg-white transition-all"></div>
          </button>
        </div>
      </header>

      {/* Mobile Menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            className="fixed inset-0 z-[100] bg-rhea-cobalt text-white overflow-hidden flex flex-col"
          >
            <div className="absolute inset-0 bg-grain opacity-40 mix-blend-overlay pointer-events-none"></div>
            
            <div className="flex justify-between items-center px-6 h-[72px] relative z-10 border-b border-white/20">
              <span className="font-serif italic font-normal text-3xl tracking-wide leading-none pt-1">Rhea</span>
              <button onClick={() => setMenuOpen(false)} className="font-sans text-[11px] uppercase tracking-[0.2em] flex items-center gap-3">
                CLOSE <span className="text-2xl font-light leading-none">×</span>
              </button>
            </div>
            
            <div className="flex-1 flex flex-col justify-center px-8 relative z-10">
              <nav className="flex flex-col gap-8 font-serif italic text-6xl tracking-wide">
                <Link to="/workspace" onClick={() => setMenuOpen(false)} className={cn("transition-opacity", location.pathname === '/workspace' ? "opacity-100" : "opacity-50 hover:opacity-100")}>Workspace</Link>
                <Link to="/search" onClick={() => setMenuOpen(false)} className={cn("transition-opacity", location.pathname === '/search' ? "opacity-100" : "opacity-50 hover:opacity-100")}>History</Link>
                <Link to="/settings" onClick={() => setMenuOpen(false)} className={cn("transition-opacity", location.pathname === '/settings' ? "opacity-100" : "opacity-50 hover:opacity-100")}>Settings</Link>
              </nav>
              
              <div className="mt-16 flex flex-col gap-6 font-sans text-[11px] uppercase tracking-[0.2em] border-t border-white/20 pt-8">
                <Link to="/" onClick={() => setMenuOpen(false)} className="text-white hover:opacity-70">EXIT RHEA ↗</Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area - Padding top for fixed header */}
      <main className="flex-1 flex flex-col relative z-10 w-full pt-[72px] lg:pt-[88px]">
        {children}
      </main>

    </div>
  );
}
