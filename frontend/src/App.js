import { Toaster } from "sonner";
import { BrowserRouter, Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import Dashboard from "@/pages/Dashboard";
import BulkVisit from "@/pages/BulkVisit";
import History from "@/pages/History";
import Appeals from "@/pages/Appeals";
import Settings from "@/pages/Settings";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ProtectedRoute from "@/components/ProtectedRoute";
import BrandMark from "@/components/BrandMark";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import "@/App.css";

const navLinkClass = ({ isActive }) =>
  `px-4 py-2 rounded-full text-sm font-medium transition-colors ${
    isActive
      ? "bg-[hsl(var(--primary))] text-primary-foreground"
      : "text-foreground/70 hover:text-foreground hover:bg-secondary"
  }`;

function UserMenu() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  if (!user) return null;
  const initial = (user.office_name || user.email || "?").slice(0, 1).toUpperCase();
  return (
    <div className="flex items-center gap-3 pl-4 border-l border-border">
      <div className="text-right leading-tight hidden sm:block">
        <div className="text-sm font-semibold" data-testid="user-office">
          {user.office_name || user.email}
        </div>
        <div className="text-xs text-muted-foreground">{user.email}</div>
      </div>
      <div className="w-9 h-9 rounded-full bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] grid place-items-center font-display font-bold">
        {initial}
      </div>
      <button
        onClick={async () => { await logout(); nav("/login", { replace: true }); }}
        data-testid="logout-btn"
        title="Sign out"
        className="text-muted-foreground hover:text-destructive p-2 rounded-full transition-colors"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}

function Shell({ children }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-card sticky top-0 z-40">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-10 py-4 flex items-center gap-6 flex-wrap">
          <BrandMark size={44} tagline="Dental Claim Assistant" />
          <nav className="ml-auto flex items-center gap-1 flex-wrap">
            <NavLink to="/" end data-testid="nav-dashboard" className={navLinkClass}>
              Single
            </NavLink>
            <NavLink to="/bulk" data-testid="nav-bulk" className={navLinkClass}>
              Visit packet
            </NavLink>
            <NavLink to="/history" data-testid="nav-history" className={navLinkClass}>
              History
            </NavLink>
            <NavLink to="/appeals" data-testid="nav-appeals" className={navLinkClass}>
              Appeals
            </NavLink>
            <NavLink to="/settings" data-testid="nav-settings" className={navLinkClass}>
              Settings
            </NavLink>
          </nav>
          <UserMenu />
        </div>
      </header>
      <main className="max-w-[1440px] mx-auto px-6 lg:px-10 py-8">{children}</main>
      <footer className="max-w-[1440px] mx-auto px-6 lg:px-10 py-6 text-xs text-muted-foreground border-t border-border mt-8">
        Narratives are AI-generated drafts for claim submission. Always verify against the patient chart before sending.
      </footer>
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Shell><Dashboard /></Shell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/bulk"
        element={
          <ProtectedRoute>
            <Shell><BulkVisit /></Shell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/history"
        element={
          <ProtectedRoute>
            <Shell><History /></Shell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/appeals"
        element={
          <ProtectedRoute>
            <Shell><Appeals /></Shell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Shell><Settings /></Shell>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster position="bottom-right" richColors closeButton />
      </AuthProvider>
    </BrowserRouter>
  );
}
