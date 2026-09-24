import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signup, ApiError } from "../api/client.js";
import { isPasswordValid } from "../lib/passwordRules.js";
import {
  PasswordRequirementsList,
  PasswordStrengthIndicator,
} from "../components/ui/PasswordStrength.jsx";
import { useToast } from "../lib/toast.jsx";
import { AsciiEffect } from "@/components/ui/ascii-effect";

export default function SignUpPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { showToast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;

    setError("");
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (!isPasswordValid(password)) {
      setError("Password does not meet requirements");
      return;
    }

    setLoading(true);
    try {
      await signup(email, password);
      showToast("Account created successfully", "success");
      navigate("/login");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail || "Registration failed");
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
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
            SYSTEM.REGISTER
          </div>
        </div>

        {/* Form Container */}
        <div className="flex-1 flex flex-col justify-center px-8 lg:px-24 xl:px-32 max-w-2xl mx-auto w-full pb-8">
          
          <h1 className="font-display text-5xl xl:text-6xl uppercase tracking-wide leading-[0.9] mb-8">
            JOIN<br/>THE SYSTEM.
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

            <div className="flex flex-col gap-2 relative mt-2">
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
              <div className="mt-4 border border-rhea-black/10 bg-white/50 p-4">
                <PasswordStrengthIndicator password={password} />
                <PasswordRequirementsList password={password} className="mt-4" />
              </div>
            </div>

            <div className="flex flex-col gap-2 relative mt-2">
              <label className="text-[10px] uppercase tracking-widest font-semibold text-rhea-black/60">
                Confirm Password
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="bg-transparent border-b border-rhea-black/20 focus:border-rhea-cobalt py-3 outline-none text-lg transition-colors"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !isPasswordValid(password)}
              className="mt-6 w-full bg-rhea-cobalt hover:bg-rhea-cobaltDeep text-white text-[11px] uppercase tracking-[0.2em] font-bold py-4 transition-colors disabled:opacity-50"
            >
              {loading ? "PROCESSING..." : "CREATE ACCOUNT"}
            </button>
          </form>

          <div className="mt-6 flex flex-col gap-4 text-center">
             <p className="text-xs text-rhea-black/60">
               Already have an account? <Link to="/login" className="text-rhea-cobalt font-semibold hover:opacity-70 transition-opacity">Sign in</Link>
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
             <span className="font-serif italic capitalize tracking-normal text-[1.1em] font-normal leading-[0.7] block mb-2">Structure,</span>
             <span className="uppercase">REVEALED.</span>
           </h2>
           <div className="h-px w-32 bg-white/30 mb-8"></div>
           <p className="font-sans text-lg font-light text-white/70">
             Create an account to run inference across the graph network and analyze deep structural propagation.
           </p>
        </div>

      </div>
    </div>
  );
}
