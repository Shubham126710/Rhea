import { useEffect, useRef } from "react";

const ASCII = [" ", "·", ".", "•", "▪"];

export default function SisyphusAscii({
  src = "/sisyphus.png",
  density = 5,
  color = "#F4F3EE",
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

      /*
       * Offscreen canvas.
       * The actual implementation can use this to sample
       * luminance from the Sisyphus artwork.
       */

      const offscreen = document.createElement("canvas");

      const sampleWidth = Math.floor(width / density);
      const aspect =
        image.naturalHeight / image.naturalWidth;

      const sampleHeight = Math.floor(sampleWidth * aspect);

      offscreen.width = sampleWidth;
      offscreen.height = sampleHeight;

      const offCtx = offscreen.getContext("2d", {
        willReadFrequently: true,
      });

      offCtx.drawImage(
        image,
        0,
        0,
        sampleWidth,
        sampleHeight
      );

      const pixels = offCtx.getImageData(
        0,
        0,
        sampleWidth,
        sampleHeight
      ).data;

      const offsetX = (width - sampleWidth * density) / 2;
      const offsetY = (height - sampleHeight * density) / 2;

      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.font = `${Math.max(3, density)}px monospace`;

      for (let y = 0; y < sampleHeight; y++) {
        for (let x = 0; x < sampleWidth; x++) {
          const index = (y * sampleWidth + x) * 4;

          const r = pixels[index];
          const g = pixels[index + 1];
          const b = pixels[index + 2];
          const a = pixels[index + 3];

          if (a < 30) continue;

          const luminance =
            (0.299 * r +
              0.587 * g +
              0.114 * b) /
            255;

          if (luminance < 0.12) continue;

          /*
           * Tiny animated signal drift.
           * Keep this extremely subtle.
           */
          const wave =
            Math.sin(
              time * 0.001 +
              x * 0.12 +
              y * 0.08
            ) * 0.35;

          const alpha =
            Math.min(
              1,
              luminance * 1.35
            ) *
            (0.75 + wave * 0.15);

          ctx.globalAlpha = alpha;

          const character =
            ASCII[
              Math.min(
                ASCII.length - 1,
                Math.floor(
                  luminance * ASCII.length
                )
              )
            ];

          if (!character.trim()) continue;

          ctx.fillStyle = color;

          ctx.fillText(
            character,
            offsetX + x * density,
            offsetY + y * density
          );
        }
      }

      ctx.globalAlpha = 1;

      animationFrame =
        requestAnimationFrame(draw);
    };

    const observer = new ResizeObserver(resize);

    observer.observe(canvas);

    image.onload = () => {
      resize();
      animationFrame =
        requestAnimationFrame(draw);
    };

    return () => {
      cancelAnimationFrame(animationFrame);
      observer.disconnect();
    };
  }, [src, density, color]);

  return (
    <div
      className="pointer-events-none absolute inset-0"
      aria-hidden="true"
    >
      <canvas
        ref={canvasRef}
        className="h-full w-full"
      />
    </div>
  );
}
