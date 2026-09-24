import { useState, useEffect } from "react";
import { motion } from "framer-motion";

export function LoadingScreen({ onComplete }) {
  const [progress, setProgress] = useState(1);

  useEffect(() => {
    let currentVal = 1;
    let timeout;
    
    const tick = () => {
      currentVal += 1; // Exactly 1 each tick, no skipping
      if (currentVal > 100) currentVal = 100;
      
      setProgress(currentVal);
      
      if (currentVal < 100) {
        // Fast start, slow end. To complete 100 frames in ~2 seconds:
        // average frame time = 20ms.
        let delay = 15; // fast middle
        if (currentVal < 20) delay = 25 - (currentVal * 0.5); // slight acceleration
        else if (currentVal > 80) delay = 15 + ((currentVal - 80) * 1.5); // deceleration at the end
        
        timeout = setTimeout(tick, delay);
      }
    };
    
    timeout = setTimeout(tick, 150); // Initial start delay
    
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (progress === 100) {
      const holdTimer = setTimeout(() => {
        onComplete();
      }, 300); // Hold briefly at 100
      return () => clearTimeout(holdTimer);
    }
  }, [progress, onComplete]);

  // Ensure 2 digit formatting (01, 02 ... 100)
  const displayValue = progress.toString().padStart(2, '0');

  return (
    <motion.div 
      className="fixed inset-0 z-[100] flex items-center justify-center bg-rhea-cobalt overflow-hidden pointer-events-none"
      initial={{ opacity: 1 }}
      exit={{ 
        opacity: 0, 
        transition: { duration: 1.0, ease: [0.22, 1, 0.36, 1] } 
      }}
    >
      <div className="relative z-10 flex items-center justify-center w-full h-full mix-blend-screen">
        {/* We use a single element and just update its text rapidly */}
        <div
          className="font-serif italic font-normal text-rhea-ivory tracking-tighter overflow-visible py-16 px-4 flex items-center justify-center"
          style={{
            fontSize: "clamp(12rem, 30vw, 32rem)",
            maxHeight: "60vh",
            lineHeight: 1
          }}
        >
          {displayValue}
        </div>
      </div>
    </motion.div>
  );
}
