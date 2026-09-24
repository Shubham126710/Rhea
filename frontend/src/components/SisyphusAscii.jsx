import { useEffect, useRef } from "react";

const ASCII = [" ", ".", "·", "•", "▪", "█"];

export default function SisyphusAscii({
  src = "/sisyphus.png",
  density = 3, // Lower density = higher resolution point cloud
}) {
  const canvasRef = useRef(null);
  const imageRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", {
      alpha: true,
    });

    const image = new Image();
    image.crossOrigin = "anonymous";
    image.src = src;
    imageRef.current = image;

    let animationFrame;
    let width = 0;
    let height = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);

      width = Math.max(1, Math.floor(rect.width));
      height = Math.max(1, Math.floor(rect.height));

      canvas.width = width * dpr;
      canvas.height = height * dpr;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = (time) => {
      ctx.clearRect(0, 0, width, height);

      if (!image.complete || !image.naturalWidth) {
        animationFrame = requestAnimationFrame(draw);
        return;
      }

      const offscreen = document.createElement("canvas");
      const sampleWidth = Math.floor(width / density);
      const aspect = image.naturalHeight / image.naturalWidth;
      const sampleHeight = Math.floor(sampleWidth * aspect);

      offscreen.width = sampleWidth;
      offscreen.height = sampleHeight;

      const offCtx = offscreen.getContext("2d", {
        willReadFrequently: true,
      });

      offCtx.drawImage(image, 0, 0, sampleWidth, sampleHeight);
      const pixels = offCtx.getImageData(0, 0, sampleWidth, sampleHeight).data;

      const offsetX = (width - sampleWidth * density) / 2;
      const offsetY = (height - sampleHeight * density) / 2;

      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.font = `${Math.max(4, density * 1.5)}px monospace`;

      for (let y = 0; y < sampleHeight; y++) {
        for (let x = 0; x < sampleWidth; x++) {
          const index = (y * sampleWidth + x) * 4;

          const r = pixels[index];
          const g = pixels[index + 1];
          const b = pixels[index + 2];
          
          // True luminance formula
          const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

          // Ignore pure black background (or very close to it)
          if (luminance < 0.05) continue;

          // Tiny animated signal drift. Keep this extremely subtle.
          const wave = Math.sin(time * 0.002 + x * 0.1 + y * 0.1) * 0.15;
          const flicker = Math.random() > 0.98 ? 0.2 : 0;
          
          // Higher opacity for visibility, maintaining the structural silhouette
          const alpha = Math.min(1, Math.max(0.15, luminance + wave + flicker));
          ctx.globalAlpha = alpha;

          // Determine character based on luminance
          let charIndex = Math.floor(luminance * ASCII.length);
          if (charIndex >= ASCII.length) charIndex = ASCII.length - 1;
          const character = ASCII[charIndex];

          if (!character.trim()) continue;

          // Dual-tone coloring based on luminance to match Rhea's palette
          if (luminance > 0.7) {
            ctx.fillStyle = "#F4F3EE"; // Ivory for highlights
          } else if (luminance > 0.4) {
            ctx.fillStyle = "rgba(244, 243, 238, 0.7)"; // Faded Ivory
          } else {
            ctx.fillStyle = "#3b82f6"; // Rhea Cobalt variant for shadows/midtones
          }

          ctx.fillText(
            character,
            offsetX + x * density,
            offsetY + y * density
          );
        }
      }

      ctx.globalAlpha = 1;
      animationFrame = requestAnimationFrame(draw);
    };

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    image.onload = () => {
      resize();
      animationFrame = requestAnimationFrame(draw);
    };

    return () => {
      cancelAnimationFrame(animationFrame);
      observer.disconnect();
    };
  }, [src, density]);

  return (
    <div className="pointer-events-none absolute inset-0 flex items-center justify-center" aria-hidden="true">
      <div className="relative w-full h-[120%] lg:w-[150%] lg:h-[150%] flex items-center justify-center -mr-[10%]">
        <canvas ref={canvasRef} className="h-full w-full object-contain" />
      </div>
    </div>
  );
}
