import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

/** Wrap any route that requires a real session. */
export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return null; // avoid a flash-redirect while the one /auth/me call is in flight
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return children;
}

/** Wrap login/sign-up so an already-authenticated user skips past them. */
export function PublicOnlyRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return null;
  if (user) {
    const params = new URLSearchParams(location.search);
    const next = params.get("next");
    return <Navigate to={next && next.startsWith("/") ? next : "/workspace"} replace />;
  }
  return children;
}
