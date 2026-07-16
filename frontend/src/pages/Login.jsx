import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { apiErrorMessage } from "@/lib/api";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back");
      nav(from, { replace: true });
    } catch (e2) {
      const msg = apiErrorMessage(e2);
      setErr(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid place-items-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-11 h-11 rounded-lg bg-[hsl(var(--primary))] text-primary-foreground grid place-items-center font-display font-black text-xl">
            N
          </div>
          <div>
            <div className="font-display font-extrabold text-xl leading-none tracking-tight">
              Narrative<span className="text-[hsl(var(--primary))]">.</span>Rx
            </div>
            <div className="label-uppercase mt-1">Dental Claim Assistant</div>
          </div>
        </div>

        <div className="clay p-8">
          <h1 className="font-display font-black text-2xl mb-1">Sign in to your office</h1>
          <p className="text-muted-foreground text-sm mb-6">
            Your narratives are scoped to your account only.
          </p>

          <form onSubmit={onSubmit} className="space-y-5" data-testid="login-form">
            <div>
              <Label className="label-uppercase mb-2 block">Email</Label>
              <Input
                type="email" required autoComplete="email" data-testid="login-email"
                value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@dentaloffice.com" className="h-11"
              />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">Password</Label>
              <Input
                type="password" required autoComplete="current-password" data-testid="login-password"
                value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••" className="h-11"
              />
            </div>
            {err && (
              <div className="text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2"
                   data-testid="login-error">
                {err}
              </div>
            )}
            <Button
              type="submit" disabled={loading} data-testid="login-submit"
              className="w-full rounded-full h-11 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground gap-2 font-semibold"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground mt-6 text-center">
            Don&apos;t have an account?{" "}
            <Link to="/register" data-testid="link-register"
              className="text-[hsl(var(--primary))] font-semibold hover:underline">
              Create one
            </Link>
          </p>
        </div>

        <p className="text-xs text-center text-muted-foreground mt-6">
          Demo: <span className="font-mono">admin@dental.com</span> / <span className="font-mono">admin123</span>
        </p>
      </div>
    </div>
  );
}
