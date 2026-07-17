import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save, Loader2, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getPracticeSettings, savePracticeSettings, apiErrorMessage } from "@/lib/api";

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
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
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

      <p className="text-xs text-muted-foreground mt-4">
        Tip: after saving, regenerate any existing appeal letter to have the AI incorporate the practice details into the signature block.
      </p>
    </div>
  );
}
