import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, ApiError } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../lib/toast.jsx";
import { AsciiEffect } from "@/components/ui/ascii-effect";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { setUser } = useAuth();
  const { showToast } = useToast();

  useEffect(() => {
    document.title = "Login | Rhea";
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    setError("");
    setLoading(true);
    try {
      const data = await login(email, password, rememberMe);
      setToken(data.access_token);
      showToast("Successfully logged in", "success");
      navigate("/workspace");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail || "Invalid email or password");
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBypass = () => {
    // Immediate bypass for tester
    setUser({ id: "tester", email: "tester@rhea.dev", name: "Tester" });
    showToast("Logged in as Tester", "success");
    navigate("/workspace");
  };

  return (
    <div className="h-screen flex font-sans selection:bg-rhea-cobalt selection:text-white overflow-hidden">
      
      {/* LEFT: OFF-WHITE AUTH PANEL (50%) */}
      <div className="w-full lg:w-1/2 flex flex-col h-full bg-rhea-ivory text-rhea-black">
        
        {/* Branding Header */}
        <div className="p-8 lg:p-12 flex items-center justify-between">
          <Link to="/" className="font-serif italic font-normal text-3xl tracking-wide hover:opacity-70 transition-opacity leading-none pt-1">
            Rhea
          </Link>
          <div className="font-mono text-[9px] uppercase tracking-widest text-rhea-black/40">
            SYSTEM.AUTH
          </div>
        </div>

        {/* Login Form Container */}
        <div className="flex-1 flex flex-col justify-center px-8 lg:px-24 xl:px-32 max-w-2xl mx-auto w-full pb-8">
          
          <h1 className="font-display text-5xl xl:text-6xl uppercase tracking-wide leading-[0.9] mb-8">
            WELCOME<br/>BACK.
          </h1>

          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            
            {error && (
              <div className="bg-red-50 text-red-600 border border-red-200 p-4 text-xs font-mono uppercase tracking-widest">
                {error}
              </div>
            )}

            <div className="flex flex-col gap-2 relative">
              <label className="text-[10px] uppercase tracking-widest font-semibold text-rhea-black/60">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-transparent border-b border-rhea-black/20 focus:border-rhea-cobalt py-3 outline-none text-lg transition-colors"
                placeholder="researcher@institute.edu"
              />
            </div>

            <div className="flex flex-col gap-2 relative mt-4">
              <label className="text-[10px] uppercase tracking-widest font-semibold text-rhea-black/60">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-transparent border-b border-rhea-black/20 focus:border-rhea-cobalt py-3 outline-none text-lg transition-colors"
                placeholder="••••••••"
              />
            </div>

            <div className="flex items-center justify-between mt-4 text-xs font-medium">
              <label className="flex items-center gap-3 cursor-pointer group">
                <div className="w-4 h-4 border border-rhea-black/30 flex items-center justify-center group-hover:border-rhea-cobalt transition-colors">
                  {rememberMe && <div className="w-2 h-2 bg-rhea-cobalt"></div>}
                </div>
                <input
                  type="checkbox"
                  className="hidden"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span className="text-rhea-black/70">Remember device</span>
              </label>
              <Link to="/reset-password" className="text-rhea-cobalt hover:opacity-70 transition-opacity">
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-6 w-full bg-rhea-cobalt hover:bg-rhea-cobaltDeep text-white text-[11px] uppercase tracking-[0.2em] font-bold py-4 transition-colors disabled:opacity-50"
            >
              {loading ? "AUTHENTICATING..." : "SIGN IN"}
            </button>
          </form>

          <div className="mt-6 flex flex-col gap-4 text-center">
             <div className="flex items-center justify-center gap-4 text-[10px] uppercase tracking-widest text-rhea-black/40">
               <span className="w-12 h-px bg-rhea-black/10"></span>
               OR
               <span className="w-12 h-px bg-rhea-black/10"></span>
             </div>
             <button
               type="button"
               onClick={handleBypass}
               disabled={loading}
               className="w-full bg-transparent border border-rhea-black/20 hover:border-rhea-cobalt hover:text-rhea-cobalt text-[11px] uppercase tracking-[0.2em] font-bold py-4 transition-colors"
             >
               BYPASS LOGIN (TESTER)
             </button>
             
             <p className="mt-4 text-xs text-rhea-black/60">
               Don't have an account? <Link to="/sign-up" className="text-rhea-cobalt font-semibold hover:opacity-70 transition-opacity">Sign up</Link>
             </p>
          </div>
        </div>
      </div>

      {/* RIGHT: FULL ELECTRIC BLUE PANEL (50%) */}
      <div className="hidden lg:flex w-1/2 bg-rhea-cobalt text-white relative flex-col justify-center p-16 overflow-hidden">
        
        {/* Texture & Ascii Graphic */}
        <div className="absolute inset-0 bg-grain opacity-40 mix-blend-overlay pointer-events-none z-10"></div>
        <div className="absolute inset-0 opacity-50 pointer-events-none mix-blend-screen">
          <AsciiEffect
            variant="flow"
            imageSrc="/images/portrait.jpg"
            chars="X#+="
            flowSpeed={0.08}
            colorMode="source"
            invert={true}
            className="w-full h-full mix-blend-screen"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-rhea-cobalt to-transparent"></div>
        </div>
        
        <div className="relative z-20 max-w-xl">
           <h2 className="font-display text-[clamp(4rem,7vw,8rem)] leading-[0.8] tracking-tight text-white mb-8">
             <span className="font-serif italic capitalize tracking-normal text-[1.1em] font-normal leading-[0.7] block mb-2">Knowledge,</span>
             <span className="uppercase">REFINED.</span>
           </h2>
           <div className="h-px w-32 bg-white/30 mb-8"></div>
           <p className="font-sans text-lg font-light text-white/70">
             Authentication required to access the Rhea structural graph environment.
           </p>
        </div>

      </div>
    </div>
  );
}
