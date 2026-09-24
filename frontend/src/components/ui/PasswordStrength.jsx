export function PasswordStrengthIndicator({ password }) {
  const strength = password.length > 8 ? 100 : password.length * 10;
  return (
    <div className="w-full h-1 bg-rhea-black/10 mt-2">
      <div 
        className="h-full bg-rhea-cobalt transition-all" 
        style={{ width: `${Math.min(100, Math.max(0, strength))}%` }}
      />
    </div>
  );
}

export function PasswordRequirementsList({ password, className }) {
  return (
    <ul className={`text-[9px] uppercase tracking-widest font-mono text-rhea-black/50 ${className || ""}`}>
      <li>{password.length >= 8 ? "✓" : "○"} At least 8 characters</li>
    </ul>
  );
}
