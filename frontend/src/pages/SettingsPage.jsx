import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteAccount, ApiError } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../lib/toast.jsx";
import { WorkspaceLayout } from "@/components/layout/WorkspaceLayout";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const { setToken } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [isDeleting, setIsDeleting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleLogout = () => {
    setToken(null);
    showToast("Logged out successfully", "success");
    navigate("/");
  };

  const handleDeleteAccount = async () => {
    if (isDeleting) return;
    setIsDeleting(true);
    try {
      await deleteAccount();
      setToken(null);
      showToast("Account deleted successfully", "success");
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        showToast(err.detail || "Failed to delete account", "error");
      } else {
        showToast("An unexpected error occurred", "error");
      }
    } finally {
      setIsDeleting(false);
      setShowConfirm(false);
    }
  };

  return (
    <WorkspaceLayout>
      <div className="flex-1 w-full flex flex-col relative overflow-hidden h-full min-h-[calc(100vh-80px)]">
        
        {/* Header Section */}
        <div className="w-full max-w-[1400px] mx-auto px-6 lg:px-[88px] pt-16 pb-12">
          <h1 className="font-sans font-light text-[clamp(4rem,7vw,8rem)] leading-[0.85] tracking-tight text-white mb-8 uppercase flex flex-col">
            <span className="font-serif italic capitalize text-[1.15em] font-normal leading-[0.7] pr-4 mb-2 text-white">System</span>
            <span className="font-semibold tracking-tighter text-white">PREFERENCES.</span>
          </h1>
          <p className="font-sans text-xl font-light text-white/60 max-w-xl">
            Configure your research environment, profile access, and destructive actions.
          </p>
        </div>

        {/* Settings Content */}
        <div className="w-full flex-1 flex flex-col bg-transparent relative z-10">
          
          <div className="max-w-[1400px] mx-auto w-full px-6 lg:px-[88px] flex flex-col pb-24">
            
            {/* Top Metadata Row */}
            <div className="border-t border-b border-white/10 py-6 flex justify-between items-center mb-16">
              <span className="font-mono text-[9px] uppercase tracking-widest text-white/40">PROFILE CONTROLS</span>
              <span className="font-mono text-[9px] uppercase tracking-widest text-white font-bold">
                ID: USR_9281
              </span>
            </div>

            {/* Session Section */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-8 mb-16">
               <div className="md:col-span-4 flex flex-col gap-4">
                 <h3 className="font-sans text-2xl font-light tracking-wide text-white uppercase">SESSION</h3>
                 <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/50 font-medium leading-relaxed">
                   Current authentication state. Terminate access token.
                 </p>
               </div>
               <div className="md:col-span-8 flex flex-col items-start border-l border-white/10 pl-8">
                 <button
                   onClick={handleLogout}
                   className="font-sans text-[11px] uppercase tracking-[0.2em] font-bold text-white hover:text-white/70 transition-colors flex items-center gap-4 group"
                 >
                   LOG OUT 
                   <span className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform">↗</span>
                 </button>
               </div>
            </div>
            
            <div className="w-full h-px bg-white/10 mb-16"></div>
            
            {/* Destruction Section */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
               <div className="md:col-span-4 flex flex-col gap-4">
                 <h3 className="font-sans text-2xl font-light tracking-wide text-white uppercase">ACCOUNT DESTRUCTION</h3>
                 <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/50 font-medium leading-relaxed">
                   Permanently purge all structural records and access.
                 </p>
               </div>
               <div className="md:col-span-8 flex flex-col border-l border-white/10 pl-8">
                 {!showConfirm ? (
                   <button
                     onClick={() => setShowConfirm(true)}
                     className="font-sans text-[11px] uppercase tracking-[0.2em] font-bold text-red-400 hover:text-red-300 transition-colors self-start"
                   >
                     DELETE ACCOUNT
                   </button>
                 ) : (
                   <div className="bg-red-500/10 border border-red-500/20 p-8 flex flex-col gap-6 max-w-xl">
                     <div className="font-mono text-[9px] uppercase tracking-widest text-red-400 font-bold">
                       WARNING: IRREVERSIBLE ACTION
                     </div>
                     <p className="font-sans text-sm font-light text-white/80 leading-relaxed">
                       Are you absolutely certain? This will completely purge your access and all your saved inferences from the Rhea system.
                     </p>
                     <div className="flex flex-col sm:flex-row gap-8 mt-4">
                       <button
                         onClick={handleDeleteAccount}
                         disabled={isDeleting}
                         className="font-sans text-[11px] uppercase tracking-[0.2em] font-bold text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
                       >
                         {isDeleting ? "PURGING..." : "CONFIRM DELETION"}
                       </button>
                       <button
                         onClick={() => setShowConfirm(false)}
                         disabled={isDeleting}
                         className="font-sans text-[11px] uppercase tracking-[0.2em] font-bold text-white/50 hover:text-white transition-colors"
                       >
                         CANCEL
                       </button>
                     </div>
                   </div>
                 )}
               </div>
            </div>

          </div>
        </div>
      </div>
    </WorkspaceLayout>
  );
}
