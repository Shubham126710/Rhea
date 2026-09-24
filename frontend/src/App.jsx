import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import { ToastProvider } from "./lib/toast.jsx";
import { ProtectedRoute, PublicOnlyRoute } from "./routes/Guards.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignUpPage from "./pages/SignUpPage.jsx";
import ResetPasswordPage from "./pages/ResetPasswordPage.jsx";
import WorkspacePage from "./pages/WorkspacePage.jsx";
import SearchPage from "./pages/SearchPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";

import LandingPage from "./pages/LandingPage.jsx";

function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center font-body-md text-on-surface">
      <div className="text-center">
        <p className="font-headline-md text-headline-md mb-2">Page not found</p>
        <a className="text-primary hover:underline" href="/">
          Return home
        </a>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
    <AuthProvider>
      <ToastProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <LoginPage />
              </PublicOnlyRoute>
            }
          />
          <Route
            path="/sign-up"
            element={
              <PublicOnlyRoute>
                <SignUpPage />
              </PublicOnlyRoute>
            }
          />
          {/* Not auth-gated either way: a logged-out visitor needs it to
              reset their password, and a logged-in visitor may still
              want to change their password via an emailed link. */}
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route
            path="/workspace"
            element={
              <ProtectedRoute>
                <WorkspacePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/search"
            element={
              <ProtectedRoute>
                <SearchPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ToastProvider>
    </AuthProvider>
    </ThemeProvider>
  );
}
