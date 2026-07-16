import { Navigate, useLocation } from "react-router-dom";
import { useMemo } from "react";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

export default function ProtectedRoute({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  const navState = useMemo(() => ({ from: location.pathname }), [location.pathname]);

  if (user === undefined) {
    return (
      <div className="min-h-screen grid place-items-center" data-testid="auth-loading">
        <Loader2 className="h-6 w-6 animate-spin text-[hsl(var(--primary))]" />
      </div>
    );
  }

  if (user === null) {
    return <Navigate to="/login" state={navState} replace />;
  }

  return children;
}
