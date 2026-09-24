import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Hero } from "@/components/landing/Hero";
import { Research } from "@/components/landing/Research";
import { Method } from "@/components/landing/Method";
import { Demo } from "@/components/landing/Demo";
import { About } from "@/components/landing/About";
import { LoadingScreen } from "@/components/landing/LoadingScreen";

export default function LandingPage() {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (isLoading) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isLoading]);
  
  // Smooth scroll configuration for internal links
  useEffect(() => {
    const handleHashChange = (e) => {
      const hash = window.location.hash;
      if (hash) {
        const target = document.querySelector(hash);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth' });
          // Update URL without jumping
          history.pushState(null, null, hash);
        }
      }
    };
    
    // Add click listeners to any anchor links starting with #
    const links = document.querySelectorAll('a[href^="/#"]');
    const handleClick = (e) => {
      const href = e.currentTarget.getAttribute('href');
      const hash = href.replace('/', '');
      const target = document.querySelector(hash);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
        history.pushState(null, null, hash);
      }
    };
    
    links.forEach(link => link.addEventListener('click', handleClick));
    
    // Handle initial load with hash
    if (window.location.hash) {
      setTimeout(() => {
         const target = document.querySelector(window.location.hash);
         if (target) target.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
    
    return () => {
      links.forEach(link => link.removeEventListener('click', handleClick));
    };
  }, []);

  return (
    <div className="bg-rhea-cobalt min-h-screen relative">
      <AnimatePresence mode="wait">
        {isLoading ? (
          <LoadingScreen key="loader" onComplete={() => setIsLoading(false)} />
        ) : (
          <motion.div 
            key="content" 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
            className="bg-rhea-ivory text-rhea-black min-h-screen font-sans selection:bg-rhea-cobalt selection:text-white relative"
          >
            <Navbar theme="blue" />

            <main>
              <Hero />
              <Research />
              <Method />
              <Demo />
              <About />
            </main>

            <Footer />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
