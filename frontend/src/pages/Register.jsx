import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import BrandMark from "@/components/BrandMark";
import { useAuth } from "@/context/AuthContext";
import { apiErrorMessage } from "@/lib/api";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [office, setOffice] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await register(email, password, office);
      toast.success(`Welcome, ${office || "office"}!`);
      nav("/", { replace: true });
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
        <div className="mb-8 flex justify-center">
          <BrandMark size={96} />
        </div>

        <div className="clay p-8">
          <h1 className="font-display font-black text-2xl mb-1">Create your office account</h1>
          <p className="text-muted-foreground text-sm mb-6">
            One account per office. All narratives and appeals stay private to you.
          </p>

          <form onSubmit={onSubmit} className="space-y-5" data-testid="register-form">
            <div>
              <Label className="label-uppercase mb-2 block">Office name</Label>
              <Input
                data-testid="register-office" value={office}
                onChange={(e) => setOffice(e.target.value)}
                placeholder="Bright Smiles Dental" className="h-11"
              />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">Email</Label>
              <Input
                type="email" required autoComplete="email" data-testid="register-email"
                value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="billing@yourpractice.com" className="h-11"
              />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">Password</Label>
              <Input
                type="password" required minLength={6} autoComplete="new-password"
                data-testid="register-password" value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 6 characters" className="h-11"
              />
            </div>
            {err && (
              <div className="text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2"
                   data-testid="register-error">
                {err}
              </div>
            )}
            <Button
              type="submit" disabled={loading} data-testid="register-submit"
              className="w-full rounded-full h-11 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground gap-2 font-semibold"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {loading ? "Creating account..." : "Create account"}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground mt-6 text-center">
            Already have an account?{" "}
            <Link to="/login" data-testid="link-login"
              className="text-[hsl(var(--primary))] font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
