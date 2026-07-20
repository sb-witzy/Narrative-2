import { useEffect, useState, useRef } from "react";
import { toast } from "sonner";
import {
  Save, Loader2, Building2, Cog, RefreshCw, Download,
  CheckCircle2, AlertCircle, GitBranch,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  getPracticeSettings, savePracticeSettings,
  getSystemVersion, checkForUpdates, startUpdate,
  apiErrorMessage,
} from "@/lib/api";

const FIELDS = [
  { key: "practice_name", label: "Practice name", placeholder: "Bright Smiles Dental", full: true },
  { key: "address_line1", label: "Address line 1", placeholder: "123 Main St", full: true },
  { key: "address_line2", label: "Address line 2", placeholder: "Suite 200 (optional)", full: true },
  { key: "city", label: "City", placeholder: "Springfield" },
  { key: "state", label: "State", placeholder: "IL" },
  { key: "zip_code", label: "ZIP", placeholder: "62701" },
  { key: "phone", label: "Phone", placeholder: "(555) 123-4567" },
  { key: "fax", label: "Fax", placeholder: "(555) 123-4568" },
  { key: "email", label: "Practice email", placeholder: "billing@yourpractice.com", full: true },
  { key: "npi", label: "NPI (National Provider ID)", placeholder: "1234567890" },
  { key: "tax_id", label: "Tax ID / EIN", placeholder: "12-3456789" },
  { key: "provider_name", label: "Treating provider name", placeholder: "Dr. Jane Smith, DDS", full: true },
  { key: "provider_license", label: "Provider license #", placeholder: "IL-DDS-12345", full: true },
];
const EMPTY = FIELDS.reduce((a, f) => ({ ...a, [f.key]: "" }), {});

function formatCommitDate(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

function SystemSection() {
  const [version, setVersion] = useState(null);
  const [versionErr, setVersionErr] = useState(null);
  const [check, setCheck] = useState(null);
  const [checking, setChecking] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [awaitingRestart, setAwaitingRestart] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    getSystemVersion()
      .then((v) => { setVersion(v); setVersionErr(null); })
      .catch((e) => setVersionErr(apiErrorMessage(e)));
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const onCheck = async () => {
    setChecking(true);
    try { setCheck(await checkForUpdates()); }
    catch (e) { toast.error(apiErrorMessage(e)); }
    finally { setChecking(false); }
  };

  const onUpdate = async () => {
    if (!window.confirm(
      "The app will restart in ~30 seconds and be unavailable to all staff for 3-5 minutes. Continue?"
    )) return;
    setUpdating(true);
    try {
      await startUpdate();
      toast.success("Update started — waiting for restart...");
      setAwaitingRestart(true);
      // Poll every 5 sec for the backend to come back with a new commit
      const originalCommit = version?.commit;
      pollRef.current = setInterval(async () => {
        try {
          const v = await getSystemVersion();
          if (v?.commit && originalCommit && v.commit !== originalCommit) {
            clearInterval(pollRef.current);
            pollRef.current = null;
            setVersion(v);
            setCheck(null);
            setAwaitingRestart(false);
            setUpdating(false);
            toast.success("Update complete! Reloading...");
            setTimeout(() => window.location.reload(), 1500);
          }
        } catch { /* backend still down — keep polling */ }
      }, 5000);
    } catch (e) {
      toast.error(apiErrorMessage(e));
      setUpdating(false);
    }
  };

  if (!version) {
    if (versionErr) {
      return (
        <div className="clay p-6 text-sm" data-testid="system-error">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-amber-900">System info unavailable</div>
              <p className="text-muted-foreground mt-1">
                The backend didn't respond to <span className="font-mono">/api/system/version</span>. Most likely your server is running an older build that doesn't have self-update yet — on the server, run <span className="font-mono">windows\update.bat</span> once (or <span className="font-mono">git pull</span> then restart the service), then reload this page.
              </p>
              <p className="text-xs text-muted-foreground mt-2">Details: {versionErr}</p>
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="clay p-6 text-sm text-muted-foreground" data-testid="system-loading">
        <Loader2 className="h-4 w-4 animate-spin inline mr-2" />
        Loading version info...
      </div>
    );
  }

  const canSelfUpdate = version.is_git_repo && version.platform === "win32";

  return (
    <div className="clay p-6 space-y-5" data-testid="system-section">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-secondary grid place-items-center">
          <Cog className="h-4 w-4 text-foreground/70" />
        </div>
        <div>
          <h2 className="font-display font-extrabold text-xl leading-none">System</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Current version and self-update controls.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
        <div>
          <Label className="label-uppercase mb-2 block">Current version</Label>
          <div className="flex items-center gap-2 flex-wrap">
            {version.commit_short ? (
              <>
                <Badge variant="outline" className="font-mono">
                  <GitBranch className="h-3 w-3 mr-1" />
                  {version.branch || "?"} · {version.commit_short}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {formatCommitDate(version.commit_date)}
                </span>
              </>
            ) : (
              <span className="text-sm text-muted-foreground">Not a git checkout</span>
            )}
          </div>
          {version.commit_message && (
            <p className="text-xs text-foreground/70 mt-2 italic">"{version.commit_message}"</p>
          )}
        </div>
        <div>
          <Label className="label-uppercase mb-2 block">Environment</Label>
          <div className="text-sm text-foreground/80">
            Platform: <span className="font-mono">{version.platform}</span>
            <br />
            <span className="text-xs text-muted-foreground font-mono break-all">{version.repo_root}</span>
          </div>
        </div>
      </div>

      <>
          <div className="pt-2 flex flex-wrap gap-2 items-center">
            <Button
              onClick={onCheck} disabled={checking || updating || !canSelfUpdate}
              data-testid="check-updates-btn"
              variant="outline" className="rounded-full gap-2 h-10"
            >
              {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              {checking ? "Checking..." : "Check for updates"}
            </Button>
            {check?.has_update && !awaitingRestart && (
              <Button
                onClick={onUpdate} disabled={updating}
                data-testid="apply-update-btn"
                className="rounded-full gap-2 h-10 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground font-semibold"
              >
                {updating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                {updating ? "Starting..." : `Install ${check.behind} update${check.behind > 1 ? "s" : ""}`}
              </Button>
            )}
          </div>

          {awaitingRestart && (
            <div className="rounded-md bg-amber-50 border border-amber-200 p-4 flex items-start gap-3" data-testid="updating-banner">
              <Loader2 className="h-5 w-5 animate-spin text-amber-700 shrink-0 mt-0.5" />
              <div className="text-sm">
                <div className="font-semibold text-amber-900">Updating Narrative.Rx</div>
                <p className="text-amber-800 mt-1">
                  The service is stopping, pulling the latest code, and rebuilding. This page will reload automatically once the update is complete (usually 2-4 minutes). Do not close the browser.
                </p>
              </div>
            </div>
          )}

          {!awaitingRestart && check && !check.has_update && (
            <div className="rounded-md bg-emerald-50 border border-emerald-200 p-3 flex items-center gap-2" data-testid="up-to-date-banner">
              <CheckCircle2 className="h-4 w-4 text-emerald-700" />
              <span className="text-sm text-emerald-900">
                You're on the latest version{check.branch ? ` of \`${check.branch}\`` : ""}.
              </span>
            </div>
          )}

          {check?.has_update && !awaitingRestart && (
            <div className="rounded-md bg-blue-50 border border-blue-200 p-3 space-y-1" data-testid="update-available-banner">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-blue-700" />
                <span className="text-sm font-semibold text-blue-900">
                  Update available: {check.behind} new commit{check.behind > 1 ? "s" : ""} on `{check.branch}`
                </span>
              </div>
              {check.latest_message && (
                <p className="text-xs text-blue-900/80 pl-6 italic">"{check.latest_message}"</p>
              )}
              <p className="text-xs text-blue-900/70 pl-6">
                Latest: <span className="font-mono">{check.latest_short}</span>
                {check.latest_date && ` · ${formatCommitDate(check.latest_date)}`}
              </p>
            </div>
          )}

          {!canSelfUpdate && (
            <div className="rounded-md bg-secondary/60 border border-border p-3 text-xs text-muted-foreground">
              Self-update is available only on Windows Server installs where the app was deployed from git. On this environment, updates must be applied manually.
            </div>
          )}
        </>
    </div>
  );
}

export default function Settings() {
  const [values, setValues] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getPracticeSettings()
      .then((data) => setValues({ ...EMPTY, ...(data || {}) }))
      .catch((e) => toast.error(apiErrorMessage(e)))
      .finally(() => setLoading(false));
  }, []);

  const update = (k) => (e) => setValues((v) => ({ ...v, [k]: e.target.value }));

  const onSave = async () => {
    setSaving(true);
    try {
      await savePracticeSettings(values);
      toast.success("Practice settings saved");
    } catch (e) {
      toast.error(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="clay p-10 text-center text-muted-foreground">
        <Loader2 className="h-6 w-6 mx-auto animate-spin text-[hsl(var(--primary))]" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-8">
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-lg bg-[hsl(var(--primary))]/10 grid place-items-center">
          <Building2 className="h-5 w-5 text-[hsl(var(--primary))]" />
        </div>
        <div>
          <h1 className="font-display font-black text-3xl tracking-tight">
            Practice settings<span className="text-[hsl(var(--primary))]">.</span>
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            These details appear at the top of every PDF (narratives, visit packets, appeal letters) and are used by the AI when drafting appeal letters.
          </p>
        </div>
      </div>

      <div className="clay p-6 space-y-5" data-testid="practice-settings-form">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {FIELDS.map((f) => (
            <div key={f.key} className={f.full ? "sm:col-span-3" : "sm:col-span-1"}>
              <Label className="label-uppercase mb-2 block">{f.label}</Label>
              <Input
                data-testid={`settings-${f.key}`}
                value={values[f.key] || ""}
                onChange={update(f.key)}
                placeholder={f.placeholder}
                className="h-10"
              />
            </div>
          ))}
        </div>

        <div className="pt-2">
          <Button
            onClick={onSave}
            disabled={saving}
            data-testid="settings-save-btn"
            className="rounded-full h-11 px-6 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground gap-2 font-semibold"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {saving ? "Saving..." : "Save practice settings"}
          </Button>
        </div>
      </div>

      <p className="text-xs text-muted-foreground -mt-4">
        Tip: after saving, regenerate any existing appeal letter to have the AI incorporate the practice details into the signature block.
      </p>

      <SystemSection />
    </div>
  );
}
