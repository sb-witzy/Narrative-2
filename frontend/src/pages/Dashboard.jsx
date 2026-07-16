import { useState, useEffect } from "react";
import { toast } from "sonner";
import {
  Copy,
  Sparkles,
  Loader2,
  Camera,
  X,
  Info,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { listProcedures, generateNarrative } from "@/lib/api";

const CATEGORY_ORDER = [
  "Crown",
  "Restorative",
  "Endodontics",
  "Extraction",
  "Periodontics",
  "Implant",
  "Bridge",
  "Surgical",
  "Occlusal Guard",
];

function groupByCategory(procs) {
  const map = {};
  procs.forEach((p) => {
    map[p.category] = map[p.category] || [];
    map[p.category].push(p);
  });
  return CATEGORY_ORDER.filter((c) => map[c]).map((c) => ({
    category: c,
    items: map[c],
  }));
}

function CopyBlock({ label, testid, text }) {
  const [flash, setFlash] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setFlash(true);
      setTimeout(() => setFlash(false), 700);
      toast.success(`${label} copied to clipboard`);
    } catch {
      toast.error("Copy failed");
    }
  };
  return (
    <div
      className={`clay p-6 relative ${flash ? "copy-flash" : ""}`}
      data-testid={`narrative-block-${testid}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="label-uppercase">{label}</span>
          <span className="text-xs text-muted-foreground">
            {text ? `${text.split(/\s+/).length} words` : ""}
          </span>
        </div>
        <Button
          onClick={onCopy}
          size="sm"
          variant="outline"
          disabled={!text}
          data-testid={`copy-${testid}`}
          className="gap-1.5 rounded-full"
        >
          <Copy className="h-3.5 w-3.5" /> Copy
        </Button>
      </div>
      <p className="text-[15px] leading-relaxed whitespace-pre-wrap text-foreground/90">
        {text || (
          <span className="text-muted-foreground italic">
            Not generated yet.
          </span>
        )}
      </p>
    </div>
  );
}

function RadiographPanel({ radiographs }) {
  if (!radiographs) return null;
  const { required = [], recommended = [], note = "" } = radiographs;
  return (
    <div className="clay p-6" data-testid="radiograph-panel">
      <div className="flex items-center gap-2 mb-4">
        <Camera className="h-4 w-4 text-[hsl(var(--primary))]" />
        <span className="label-uppercase">Radiographs to submit</span>
      </div>
      {required.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-semibold text-foreground/80 mb-2">
            Required
          </div>
          <div className="flex flex-wrap gap-2">
            {required.map((r) => (
              <Badge
                key={r}
                data-testid={`xray-required-${r}`}
                className="bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-primary-foreground rounded-full px-3 py-1"
              >
                <Check className="h-3 w-3 mr-1" /> {r}
              </Badge>
            ))}
          </div>
        </div>
      )}
      {recommended.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-semibold text-foreground/80 mb-2">
            Recommended
          </div>
          <div className="flex flex-wrap gap-2">
            {recommended.map((r) => (
              <Badge
                key={r}
                variant="outline"
                data-testid={`xray-recommended-${r}`}
                className="rounded-full px-3 py-1 border-[hsl(var(--warning))] text-[hsl(var(--warning))]"
              >
                {r}
              </Badge>
            ))}
          </div>
        </div>
      )}
      {required.length === 0 && recommended.length === 0 && (
        <div className="text-sm text-muted-foreground">
          No radiographs typically required for this procedure.
        </div>
      )}
      {note && (
        <div className="mt-4 text-sm text-foreground/80 bg-secondary/60 rounded-md p-3 border border-border flex gap-2">
          <Info className="h-4 w-4 mt-0.5 shrink-0 text-[hsl(var(--primary))]" />
          <span>{note}</span>
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [procedures, setProcedures] = useState([]);
  const [form, setForm] = useState({
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
  });
  const [selectedProc, setSelectedProc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    listProcedures()
      .then(setProcedures)
      .catch(() => toast.error("Failed to load procedures"));
  }, []);

  const grouped = groupByCategory(procedures);

  const update = (k) => (e) =>
    setForm((f) => ({ ...f, [k]: e?.target ? e.target.value : e }));

  const onProcedureChange = (code) => {
    setForm((f) => ({ ...f, procedure_code: code }));
    const p = procedures.find((x) => x.code === code);
    setSelectedProc(p);
  };

  const canGenerate = !!form.procedure_code && !loading;

  const onGenerate = async () => {
    if (!canGenerate) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await generateNarrative(form);
      setResult(data);
      toast.success("Narratives generated");
    } catch (err) {
      toast.error(
        err?.response?.data?.detail || "Generation failed. Please retry."
      );
    } finally {
      setLoading(false);
    }
  };

  const onReset = () => {
    setForm({
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
    });
    setSelectedProc(null);
    setResult(null);
  };

  const radiographs =
    result?.radiographs ||
    (selectedProc ? selectedProc.radiographs : null);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      {/* LEFT: form */}
      <section
        className="col-span-12 lg:col-span-5 xl:col-span-5"
        data-testid="clinical-form"
      >
        <div className="mb-6">
          <h1 className="font-display font-black text-3xl sm:text-4xl tracking-tight">
            Write a claim narrative
            <span className="text-[hsl(var(--primary))]">.</span>
          </h1>
          <p className="text-muted-foreground mt-2 text-[15px] leading-relaxed">
            Enter the procedure and clinical details. We&apos;ll draft a short
            remark and a full narrative, plus tell you which radiographs the
            carrier expects.
          </p>
        </div>

        <div className="clay p-6 space-y-5">
          <div>
            <Label className="label-uppercase mb-2 block">Procedure</Label>
            <Select
              value={form.procedure_code}
              onValueChange={onProcedureChange}
            >
              <SelectTrigger
                data-testid="procedure-select"
                className="h-12 text-base"
              >
                <SelectValue placeholder="Select CDT code / procedure..." />
              </SelectTrigger>
              <SelectContent className="max-h-[420px]">
                {grouped.map((g) => (
                  <SelectGroup key={g.category}>
                    <SelectLabel>{g.category}</SelectLabel>
                    {g.items.map((p) => (
                      <SelectItem
                        key={p.code}
                        value={p.code}
                        data-testid={`procedure-option-${p.code}`}
                      >
                        <span className="font-mono text-xs mr-2 text-[hsl(var(--primary))]">
                          {p.code}
                        </span>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="tooth" className="label-uppercase mb-2 block">
                Tooth #
              </Label>
              <Input
                id="tooth"
                data-testid="input-tooth"
                value={form.tooth_number}
                onChange={update("tooth_number")}
                placeholder="e.g., 30"
                disabled={selectedProc && !selectedProc.requires_tooth}
              />
            </div>
            <div>
              <Label htmlFor="surfaces" className="label-uppercase mb-2 block">
                Surfaces
              </Label>
              <Input
                id="surfaces"
                data-testid="input-surfaces"
                value={form.surfaces}
                onChange={update("surfaces")}
                placeholder="e.g., MOD"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="symptoms" className="label-uppercase mb-2 block">
              Chief complaint / symptoms
            </Label>
            <Textarea
              id="symptoms"
              data-testid="input-symptoms"
              rows={2}
              value={form.symptoms}
              onChange={update("symptoms")}
              placeholder="Sharp pain to cold lasting 30s, spontaneous throbbing at night..."
            />
          </div>

          <div>
            <Label
              htmlFor="clinical"
              className="label-uppercase mb-2 block"
            >
              Clinical findings
            </Label>
            <Textarea
              id="clinical"
              data-testid="input-clinical"
              rows={2}
              value={form.clinical_findings}
              onChange={update("clinical_findings")}
              placeholder="Fractured MB cusp, deep decay under existing amalgam, tooth non-restorable..."
            />
          </div>

          <div>
            <Label
              htmlFor="rads"
              className="label-uppercase mb-2 block"
            >
              Radiographic findings
            </Label>
            <Textarea
              id="rads"
              data-testid="input-rads"
              rows={2}
              value={form.radiographic_findings}
              onChange={update("radiographic_findings")}
              placeholder="Periapical radiolucency at apex of #30, widened PDL..."
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label className="label-uppercase mb-2 block">Pulp status</Label>
              <Input
                data-testid="input-pulp"
                value={form.pulp_status}
                onChange={update("pulp_status")}
                placeholder="Necrotic / irreversible pulpitis"
              />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">
                Perio findings
              </Label>
              <Input
                data-testid="input-perio"
                value={form.perio_findings}
                onChange={update("perio_findings")}
                placeholder="5-7mm pockets, class II furcation"
              />
            </div>
          </div>

          <div>
            <Label className="label-uppercase mb-2 block">
              Additional notes
            </Label>
            <Textarea
              rows={2}
              data-testid="input-notes"
              value={form.additional_notes}
              onChange={update("additional_notes")}
              placeholder="Prior RCT #30 (2018), post-op sensitivity ongoing..."
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label className="label-uppercase mb-2 block">
                Date of service
              </Label>
              <Input
                type="date"
                data-testid="input-dos"
                value={form.date_of_service}
                onChange={update("date_of_service")}
              />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">
                Patient label <span className="normal-case tracking-normal text-[10px] text-muted-foreground">(no PHI)</span>
              </Label>
              <Input
                data-testid="input-patient-label"
                value={form.patient_label}
                onChange={update("patient_label")}
                placeholder="Pt #1024"
              />
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <Button
              onClick={onGenerate}
              disabled={!canGenerate}
              data-testid="generate-btn"
              className="rounded-full h-12 px-6 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground gap-2 font-semibold"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {loading ? "Drafting..." : "Generate narrative"}
            </Button>
            <Button
              variant="ghost"
              onClick={onReset}
              data-testid="reset-btn"
              className="rounded-full gap-1"
            >
              <X className="h-4 w-4" /> Clear
            </Button>
          </div>
        </div>
      </section>

      {/* RIGHT: outputs */}
      <section
        className="col-span-12 lg:col-span-7 xl:col-span-7 space-y-6"
        data-testid="output-workspace"
      >
        {selectedProc && (
          <div className="clay p-5 flex items-start justify-between gap-4">
            <div>
              <div className="label-uppercase mb-1">Selected</div>
              <div className="font-display font-bold text-lg leading-tight">
                {selectedProc.name}
              </div>
              <div className="text-xs text-muted-foreground mt-1 font-mono">
                CDT {selectedProc.code} · {selectedProc.category}
              </div>
            </div>
          </div>
        )}

        <CopyBlock
          label="Short narrative"
          testid="short"
          text={result?.short_narrative}
        />
        <CopyBlock
          label="Long narrative"
          testid="long"
          text={result?.long_narrative}
        />

        <RadiographPanel radiographs={radiographs} />

        {!result && !selectedProc && (
          <div className="clay p-10 text-center" data-testid="empty-state">
            <div className="w-14 h-14 mx-auto rounded-full bg-secondary grid place-items-center mb-4">
              <Sparkles className="h-6 w-6 text-[hsl(var(--primary))]" />
            </div>
            <div className="font-display font-bold text-xl">
              Pick a procedure to begin
            </div>
            <p className="text-muted-foreground text-sm mt-2 max-w-md mx-auto">
              Choose a CDT code on the left, add whatever clinical details you
              have, and click Generate. Everything you enter stays on your
              office&apos;s account.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
