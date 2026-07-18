import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Sparkles, Loader2, X, FileDown, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import NarrativeCard from "@/components/NarrativeCard";
import RadiographPanel from "@/components/RadiographPanel";
import ProcedureSelect from "@/components/ProcedureSelect";
import CarrierSelect from "@/components/CarrierSelect";
import ToothPicker from "@/components/ToothPicker";
import {
  listProcedures,
  listCarriers,
  generateNarrative,
  regenerateField,
  updateHistoryItem,
  exportPdf,
  exportTxt,
} from "@/lib/api";

const EMPTY_FORM = {
  procedure_code: "",
  tooth_number: "",
  surfaces: "",
  symptoms: "",
  clinical_findings: "",
  radiographic_findings: "",
  pulp_status: "",
  perio_findings: "",
  prior_treatment: "",
  date_of_service: "",
  additional_notes: "",
  patient_label: "",
  carrier: "generic",
};

export default function Dashboard() {
  const [procedures, setProcedures] = useState([]);
  const [carriers, setCarriers] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [selectedProc, setSelectedProc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [regenLoading, setRegenLoading] = useState({ short: false, long: false });
  const [result, setResult] = useState(null);

  useEffect(() => {
    listProcedures().then(setProcedures).catch(() => toast.error("Failed to load procedures"));
    listCarriers().then(setCarriers).catch(() => toast.error("Failed to load carriers"));
  }, []);

  const update = (k) => (e) => setForm((f) => ({ ...f, [k]: e?.target ? e.target.value : e }));

  const onProcedureChange = (code) => {
    setForm((f) => ({ ...f, procedure_code: code }));
    setSelectedProc(procedures.find((x) => x.code === code));
  };

  const canGenerate = !!form.procedure_code && !loading;

  const persistEdit = async (field, value) => {
    if (!result) return;
    const next = { ...result, [field]: value };
    setResult(next);
    if (result.id) {
      try {
        await updateHistoryItem(result.id, { [field]: value });
        toast.success("Saved");
      } catch {
        toast.error("Failed to save edit");
      }
    }
  };

  const onGenerate = async () => {
    if (!canGenerate) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await generateNarrative(form);
      setResult(data);
      toast.success("Narratives generated");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Generation failed. Please retry.");
    } finally {
      setLoading(false);
    }
  };

  const onRegenerate = async (field) => {
    if (!result || regenLoading[field]) return;
    setRegenLoading((s) => ({ ...s, [field]: true }));
    try {
      const payload = {
        ...form,
        field,
        existing_short: result.short_narrative,
        existing_long: result.long_narrative,
      };
      const data = await regenerateField(payload);
      const key = `${field}_narrative`;
      const next = { ...result, [key]: data.text };
      setResult(next);
      if (result.id) {
        await updateHistoryItem(result.id, { [key]: data.text });
      }
      toast.success(`${field === "short" ? "Short" : "Long"} narrative regenerated`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Regenerate failed");
    } finally {
      setRegenLoading((s) => ({ ...s, [field]: false }));
    }
  };

  const onReset = () => {
    setForm(EMPTY_FORM);
    setSelectedProc(null);
    setResult(null);
  };

  const onExportPdf = async () => {
    if (!result) return;
    try {
      await exportPdf(result);
      toast.success("PDF downloaded");
    } catch {
      toast.error("PDF export failed");
    }
  };
  const onExportTxt = async () => {
    if (!result) return;
    try {
      await exportTxt(result);
      toast.success("Text downloaded");
    } catch {
      toast.error("Text export failed");
    }
  };

  const radiographs = result?.radiographs || (selectedProc ? selectedProc.radiographs : null);
  const toothDisabled = selectedProc && !selectedProc.requires_tooth;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="col-span-12 lg:col-span-5 xl:col-span-5" data-testid="clinical-form">
        <div className="mb-6">
          <h1 className="font-display font-black text-3xl sm:text-4xl tracking-tight">
            Write a claim narrative<span className="text-[hsl(var(--primary))]">.</span>
          </h1>
          <p className="text-muted-foreground mt-2 text-[15px] leading-relaxed">
            Pick a procedure, add whatever clinical details you have, and we&apos;ll draft
            a short remark plus a full narrative tuned to your carrier.
          </p>
        </div>

        <div className="clay p-6 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <Label className="label-uppercase mb-2 block">Procedure</Label>
              <ProcedureSelect
                value={form.procedure_code}
                onChange={onProcedureChange}
                procedures={procedures}
              />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">Carrier</Label>
              <CarrierSelect
                value={form.carrier}
                onChange={update("carrier")}
                carriers={carriers}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="label-uppercase mb-2 block">Tooth #</Label>
              {toothDisabled ? (
                <Input value="N/A" disabled className="h-10" data-testid="input-tooth-disabled" />
              ) : (
                <ToothPicker
                  value={form.tooth_number}
                  onChange={update("tooth_number")}
                  triggerLabel="Pick tooth..."
                  testid="tooth-picker"
                />
              )}
            </div>
            <div>
              <Label htmlFor="surfaces" className="label-uppercase mb-2 block">Surfaces</Label>
              <Input
                id="surfaces" data-testid="input-surfaces"
                value={form.surfaces} onChange={update("surfaces")} placeholder="e.g., MOD"
                className="h-10"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="symptoms" className="label-uppercase mb-2 block">Chief complaint / symptoms</Label>
            <Textarea id="symptoms" data-testid="input-symptoms" rows={2}
              value={form.symptoms} onChange={update("symptoms")}
              placeholder="Sharp pain to cold lasting 30s, spontaneous throbbing at night..." />
          </div>

          <div>
            <Label htmlFor="clinical" className="label-uppercase mb-2 block">Clinical findings</Label>
            <Textarea id="clinical" data-testid="input-clinical" rows={2}
              value={form.clinical_findings} onChange={update("clinical_findings")}
              placeholder="Fractured MB cusp, deep decay under existing amalgam, non-restorable..." />
          </div>

          <div>
            <Label htmlFor="rads" className="label-uppercase mb-2 block">Radiographic findings</Label>
            <Textarea id="rads" data-testid="input-rads" rows={2}
              value={form.radiographic_findings} onChange={update("radiographic_findings")}
              placeholder="Periapical radiolucency at apex of #30, widened PDL..." />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label className="label-uppercase mb-2 block">Pulp status</Label>
              <Input data-testid="input-pulp" value={form.pulp_status}
                onChange={update("pulp_status")} placeholder="Necrotic / irreversible pulpitis" />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">Perio findings</Label>
              <Input data-testid="input-perio" value={form.perio_findings}
                onChange={update("perio_findings")} placeholder="5-7mm pockets, class II furcation" />
            </div>
          </div>

          <div>
            <Label className="label-uppercase mb-2 block">Additional notes</Label>
            <Textarea rows={2} data-testid="input-notes" value={form.additional_notes}
              onChange={update("additional_notes")}
              placeholder="Prior RCT #30 (2018), post-op sensitivity ongoing..." />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label className="label-uppercase mb-2 block">Date of service</Label>
              <Input type="date" data-testid="input-dos" value={form.date_of_service}
                onChange={update("date_of_service")} className="h-10" />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">
                Patient label{" "}
                <span className="normal-case tracking-normal text-[10px] text-muted-foreground">(no PHI)</span>
              </Label>
              <Input data-testid="input-patient-label" value={form.patient_label}
                onChange={update("patient_label")} placeholder="Pt #1024" className="h-10" />
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <Button onClick={onGenerate} disabled={!canGenerate} data-testid="generate-btn"
              className="rounded-full h-12 px-6 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground gap-2 font-semibold">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {loading ? "Drafting..." : "Generate narrative"}
            </Button>
            <Button variant="ghost" onClick={onReset} data-testid="reset-btn" className="rounded-full gap-1">
              <X className="h-4 w-4" /> Clear
            </Button>
          </div>
        </div>
      </section>

      <section className="col-span-12 lg:col-span-7 xl:col-span-7 space-y-6" data-testid="output-workspace">
        {selectedProc && (
          <div className="clay p-5 flex items-start justify-between gap-4">
            <div>
              <div className="label-uppercase mb-1">Selected</div>
              <div className="font-display font-bold text-lg leading-tight">{selectedProc.name}</div>
              <div className="text-xs text-muted-foreground mt-1 font-mono">
                CDT {selectedProc.code} · {selectedProc.category}
                {form.carrier && form.carrier !== "generic" && (
                  <> · Tuned for <span className="text-[hsl(var(--primary))]">{form.carrier}</span></>
                )}
              </div>
            </div>
            {result && (
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={onExportPdf}
                  data-testid="export-pdf-btn" className="rounded-full gap-1.5">
                  <FileDown className="h-3.5 w-3.5" /> PDF
                </Button>
                <Button size="sm" variant="outline" onClick={onExportTxt}
                  data-testid="export-txt-btn" className="rounded-full gap-1.5">
                  <FileText className="h-3.5 w-3.5" /> TXT
                </Button>
              </div>
            )}
          </div>
        )}

        <NarrativeCard
          label="Short narrative"
          testid="short"
          text={result?.short_narrative}
          subjectHint={selectedProc ? `CDT ${selectedProc.code} — ${selectedProc.name}${form.tooth_number ? ` · Tooth #${form.tooth_number}` : ""}` : ""}
          onChange={(v) => persistEdit("short_narrative", v)}
          onRegenerate={result ? () => onRegenerate("short") : null}
          regenerating={regenLoading.short}
        />
        <NarrativeCard
          label="Long narrative"
          testid="long"
          text={result?.long_narrative}
          subjectHint={selectedProc ? `CDT ${selectedProc.code} — ${selectedProc.name}${form.tooth_number ? ` · Tooth #${form.tooth_number}` : ""}` : ""}
          onChange={(v) => persistEdit("long_narrative", v)}
          onRegenerate={result ? () => onRegenerate("long") : null}
          regenerating={regenLoading.long}
        />

        <RadiographPanel radiographs={radiographs} />

        {!result && !selectedProc && (
          <div className="clay p-10 text-center" data-testid="empty-state">
            <div className="w-14 h-14 mx-auto rounded-full bg-secondary grid place-items-center mb-4">
              <Sparkles className="h-6 w-6 text-[hsl(var(--primary))]" />
            </div>
            <div className="font-display font-bold text-xl">Pick a procedure to begin</div>
            <p className="text-muted-foreground text-sm mt-2 max-w-md mx-auto">
              Choose a CDT code on the left, add whatever clinical details you have,
              then click Generate.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
