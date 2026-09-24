import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

export function Navbar({ theme = "blue" }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState("");

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
      
      // Determine active section
      const sections = ['research', 'method', 'demo', 'about'];
      let current = '';
      
      for (const section of sections) {
        const el = document.getElementById(section);
        if (el) {
          const rect = el.getBoundingClientRect();
          // If the top of the section is above the middle of the screen
          if (rect.top <= window.innerHeight / 2) {
            current = section;
          }
        }
      }
      setActiveSection(current);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const isBlue = theme === "blue";
  
  const navClass = scrolled
    ? isBlue 
      ? "bg-rhea-cobalt/95 backdrop-blur-md border-b border-white/10" 
      : "bg-rhea-ivory/95 backdrop-blur-md border-b border-rhea-black/10"
    : isBlue
      ? "bg-transparent border-b border-white/20"
      : "bg-transparent border-b border-rhea-black/10";

  const textClass = isBlue ? "text-white" : "text-rhea-black";
  
  const buttonClass = isBlue 
    ? "text-white border-white/30 hover:bg-white hover:text-rhea-cobalt" 
    : "text-rhea-black border-rhea-black/30 hover:bg-rhea-black hover:text-white";

  return (
    <>
      <nav className={cn(
        "fixed top-0 left-0 w-full z-50 h-[72px] lg:h-[88px] transition-all duration-300",
        navClass, textClass
      )}>
        {/* We use a relative container to allow absolute centering of the logo */}
        <div className="relative flex items-center justify-between w-full h-full px-6 lg:px-[88px]">
          
          {/* MOBILE: Left Spacer */}
          <div className="md:hidden w-8"></div>
          
          {/* DESKTOP LEFT NAV */}
          <div className="hidden md:flex flex-1 justify-end items-center gap-12 pr-[10vw]">
            <a 
              href="/#research" 
              className={cn(
                "font-sans text-[10px] lg:text-[11px] uppercase tracking-[0.2em] font-medium transition-all relative",
                activeSection === 'research' ? "opacity-100" : "opacity-50 hover:opacity-100"
              )}
            >
              Research
              {activeSection === 'research' && (
                <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-1 h-1 bg-current rounded-full"></span>
              )}
            </a>
            <a 
              href="/#method" 
              className={cn(
                "font-sans text-[10px] lg:text-[11px] uppercase tracking-[0.2em] font-medium transition-all relative",
                activeSection === 'method' ? "opacity-100" : "opacity-50 hover:opacity-100"
              )}
            >
              Method
              {activeSection === 'method' && (
                <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-1 h-1 bg-current rounded-full"></span>
              )}
            </a>
          </div>

          {/* ABSOLUTE CENTER: BRAND */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex justify-center items-center pointer-events-none">
            <Link 
              to="/" 
              className="font-serif italic font-normal text-3xl lg:text-[2.5rem] tracking-wide hover:opacity-70 transition-opacity pointer-events-auto leading-none pt-1"
            >
              Rhea
            </Link>
          </div>

          {/* DESKTOP RIGHT NAV */}
          <div className="hidden md:flex flex-1 justify-start items-center gap-12 pl-[10vw]">
            <a 
              href="/#demo" 
              className={cn(
                "font-sans text-[10px] lg:text-[11px] uppercase tracking-[0.2em] font-medium transition-all relative",
                activeSection === 'demo' ? "opacity-100" : "opacity-50 hover:opacity-100"
              )}
            >
              Demo
              {activeSection === 'demo' && (
                <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-1 h-1 bg-current rounded-full"></span>
              )}
            </a>
            <a 
              href="/#about" 
              className={cn(
                "font-sans text-[10px] lg:text-[11px] uppercase tracking-[0.2em] font-medium transition-all relative",
                activeSection === 'about' ? "opacity-100" : "opacity-50 hover:opacity-100"
              )}
            >
              About
              {activeSection === 'about' && (
                <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-1 h-1 bg-current rounded-full"></span>
              )}
            </a>
          </div>

          {/* FAR RIGHT CTA (Desktop only) & MOBILE MENU */}
          <div className="flex items-center gap-6 absolute right-6 lg:right-[88px] top-1/2 -translate-y-1/2">
            <Link
              to="/workspace"
              className={cn(
                "hidden xl:inline-flex font-sans text-[10px] uppercase tracking-[0.15em] font-medium px-5 py-2.5 border transition-colors items-center",
                buttonClass
              )}
            >
              ENTER RHEA ↗
            </Link>
            
            <button 
              className="md:hidden flex flex-col gap-1.5 p-2 z-50 group"
              onClick={() => setMenuOpen(true)}
            >
              <div className={cn("w-6 h-[1px] transition-all", isBlue ? "bg-white" : "bg-rhea-black group-hover:w-8")}></div>
              <div className={cn("w-6 h-[1px] transition-all", isBlue ? "bg-white" : "bg-rhea-black group-hover:w-4")}></div>
            </button>
          </div>
          
        </div>
      </nav>

      {/* Full-Screen Mobile Menu */}
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
                <a href="/#research" onClick={() => setMenuOpen(false)} className="hover:opacity-70 transition-opacity">Research</a>
                <a href="/#method" onClick={() => setMenuOpen(false)} className="hover:opacity-70 transition-opacity">Method</a>
                <a href="/#demo" onClick={() => setMenuOpen(false)} className="hover:opacity-70 transition-opacity">Demo</a>
                <a href="/#about" onClick={() => setMenuOpen(false)} className="hover:opacity-70 transition-opacity">About</a>
              </nav>
              
              <div className="mt-16 flex flex-col gap-6 font-sans text-[11px] uppercase tracking-[0.2em] border-t border-white/20 pt-8">
                <Link to="/workspace" onClick={() => setMenuOpen(false)} className="text-white hover:opacity-70">ENTER RHEA ↗</Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
