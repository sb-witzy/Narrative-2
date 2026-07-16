import { Toaster } from "sonner";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "@/pages/Dashboard";
import History from "@/pages/History";
import "@/App.css";

function Shell({ children }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-card sticky top-0 z-40">
        <div className="max-w-[1440px] mx-auto px-6 lg:px-10 py-4 flex items-center gap-8">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[hsl(var(--primary))] text-primary-foreground grid place-items-center font-display font-black text-lg">
              N
            </div>
            <div>
              <div className="font-display font-extrabold text-lg leading-none tracking-tight">
                Narrative<span className="text-[hsl(var(--primary))]">.</span>Rx
              </div>
              <div className="label-uppercase mt-1">Dental Claim Assistant</div>
            </div>
          </div>
          <nav className="ml-auto flex items-center gap-1">
            <NavLink
              to="/"
              end
              data-testid="nav-dashboard"
              className={({ isActive }) =>
                `px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-[hsl(var(--primary))] text-primary-foreground"
                    : "text-foreground/70 hover:text-foreground hover:bg-secondary"
                }`
              }
            >
              Generate
            </NavLink>
            <NavLink
              to="/history"
              data-testid="nav-history"
              className={({ isActive }) =>
                `px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-[hsl(var(--primary))] text-primary-foreground"
                    : "text-foreground/70 hover:text-foreground hover:bg-secondary"
                }`
              }
            >
              History
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="max-w-[1440px] mx-auto px-6 lg:px-10 py-8">{children}</main>
      <footer className="max-w-[1440px] mx-auto px-6 lg:px-10 py-6 text-xs text-muted-foreground border-t border-border mt-8">
        Narratives are AI-generated drafts for claim submission. Always verify against the patient chart before sending.
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </Shell>
      <Toaster position="bottom-right" richColors closeButton />
    </BrowserRouter>
  );
}
