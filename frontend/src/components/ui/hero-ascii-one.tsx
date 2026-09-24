import { useEffect, useRef } from "react";

export function HeroAsciiOne({ projectId = "P21p3cTh5Jv6kQZc1K3M", className = "" }) {
  const containerRef = useRef(null);

  useEffect(() => {
    // Prevent repeated injection
    const scriptId = "unicorn-studio-script";
    let script = document.getElementById(scriptId);

    if (!script) {
      script = document.createElement("script");
      script.id = scriptId;
      script.src = "https://cdn.unicorn.studio/v1.2.1/unicornStudio.umd.js";
      script.async = true;
      document.body.appendChild(script);
    }

    const initUnicorn = () => {
      if (window.UnicornStudio && containerRef.current) {
        // Initialize the specific project within the container
        window.UnicornStudio.init({
          projectId: projectId,
          element: containerRef.current,
        });
      }
    };

    if (window.UnicornStudio) {
      initUnicorn();
    } else {
      script.addEventListener("load", initUnicorn);
    }

    return () => {
      // Cleanup to prevent memory leaks and duplicate canvases
      script?.removeEventListener("load", initUnicorn);
      if (window.UnicornStudio && containerRef.current) {
        try {
          // Attempt graceful destroy if supported by the library
          window.UnicornStudio.destroy(projectId);
        } catch (e) {
          // Fallback if destroy is not exposed
        }
      }
    };
  }, [projectId]);

  return (
    <div 
      ref={containerRef}
      className={`unicorn-embed ${className}`}
      data-us-project={projectId}
    />
  );
}
