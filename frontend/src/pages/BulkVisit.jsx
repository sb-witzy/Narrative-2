import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Plus, Trash2, Sparkles, Loader2, FileDown, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import ProcedureSelect from "@/components/ProcedureSelect";
import CarrierSelect from "@/components/CarrierSelect";
import ToothPicker from "@/components/ToothPicker";
import NarrativeCard from "@/components/NarrativeCard";
import RadiographPanel from "@/components/RadiographPanel";
import {
  listProcedures,
  listCarriers,
  generateVisit,
  updateHistoryItem,
  exportVisitPdf,
  exportVisitTxt,
} from "@/lib/api";

const emptyRow = () => ({
  _key: (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : `row-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  procedure_code: "",
  tooth_number: "",
  surfaces: "",
  clinical_findings: "",
  radiographic_findings: "",
  additional_notes: "",
});

export default function BulkVisit() {
  const [procedures, setProcedures] = useState([]);
  const [carriers, setCarriers] = useState([]);
  const [patientLabel, setPatientLabel] = useState("");
  const [carrier, setCarrier] = useState("generic");
  const [dateOfService, setDateOfService] = useState("");
  const [visitNotes, setVisitNotes] = useState("");
  const [rows, setRows] = useState([emptyRow()]);
  const [loading, setLoading] = useState(false);
  const [visit, setVisit] = useState(null);

  useEffect(() => {
    listProcedures().then(setProcedures).catch(() => toast.error("Failed to load procedures"));
    listCarriers().then(setCarriers).catch(() => toast.error("Failed to load carriers"));
  }, []);

  const updateRow = (idx, patch) =>
    setRows((rs) => rs.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  const addRow = () => setRows((rs) => [...rs, emptyRow()]);
  const removeRow = (idx) =>
    setRows((rs) => (rs.length === 1 ? [emptyRow()] : rs.filter((_, i) => i !== idx)));

  const validRows = rows
    .filter((r) => r.procedure_code)
    .map(({ _key, ...rest }) => rest);
  const canGenerate = validRows.length > 0 && !loading;

  const onGenerate = async () => {
    if (!canGenerate) return;
    setLoading(true);
    setVisit(null);
    try {
      const payload = {
        patient_label: patientLabel,
        carrier,
        date_of_service: dateOfService,
        visit_notes: visitNotes,
        procedures: validRows,
      };
      const data = await generateVisit(payload);
      setVisit(data);
      toast.success(`${data.records.length} narrative${data.records.length === 1 ? "" : "s"} generated`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const onEditRecord = async (recordId, field, value) => {
    if (!visit) return;
    const next = {
      ...visit,
      records: visit.records.map((r) =>
        r.id === recordId ? { ...r, [field]: value } : r
      ),
    };
    setVisit(next);
    try {
      await updateHistoryItem(recordId, { [field]: value });
      toast.success("Saved");
    } catch {
      toast.error("Failed to save edit");
    }
  };

  const onExportPdf = async () => {
    if (!visit) return;
    try {
      await exportVisitPdf(visit);
      toast.success("Visit packet PDF downloaded");
    } catch {
      toast.error("PDF export failed");
    }
  };
  const onExportTxt = async () => {
    if (!visit) return;
    try {
      await exportVisitTxt(visit);
      toast.success("Visit packet text downloaded");
    } catch {
      toast.error("Text export failed");
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
      <section className="xl:col-span-6" data-testid="bulk-form">
        <div className="mb-6">
          <h1 className="font-display font-black text-3xl sm:text-4xl tracking-tight">
            Multi-procedure visit<span className="text-[hsl(var(--primary))]">.</span>
          </h1>
          <p className="text-muted-foreground mt-2 text-[15px] leading-relaxed">
            Add every procedure completed at this visit. Shared context is applied to each
            narrative and the whole packet exports as a single PDF.
          </p>
        </div>

        <div className="clay p-6 space-y-5 mb-6">
          <div className="label-uppercase">Visit context</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <Label className="label-uppercase mb-2 block">Patient label</Label>
              <Input value={patientLabel} onChange={(e) => setPatientLabel(e.target.value)}
                data-testid="bulk-patient-label" placeholder="Pt #1024" className="h-10" />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">Carrier</Label>
              <CarrierSelect value={carrier} onChange={setCarrier} carriers={carriers}
                testid="bulk-carrier-select" />
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">Date of service</Label>
              <Input type="date" value={dateOfService}
                onChange={(e) => setDateOfService(e.target.value)}
                data-testid="bulk-dos" className="h-10" />
            </div>
          </div>
          <div>
            <Label className="label-uppercase mb-2 block">Shared visit notes</Label>
            <Textarea rows={2} value={visitNotes} onChange={(e) => setVisitNotes(e.target.value)}
              data-testid="bulk-visit-notes"
              placeholder="History of bruxism, high caries risk, on bisphosphonate therapy..." />
          </div>
        </div>

        <div className="space-y-4">
          {rows.map((row, idx) => {
            const proc = procedures.find((p) => p.code === row.procedure_code);
            return (
              <div key={row._key} className="clay p-5 space-y-4" data-testid={`bulk-row-${idx}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-7 h-7 rounded-full bg-[hsl(var(--primary))] text-primary-foreground grid place-items-center font-mono text-xs font-bold">
                      {idx + 1}
                    </span>
                    {proc && (
                      <Badge variant="outline" className="rounded-full font-mono">
                        {proc.category}
                      </Badge>
                    )}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => removeRow(idx)}
                    data-testid={`bulk-remove-${idx}`}
                    className="rounded-full text-muted-foreground hover:text-destructive gap-1">
                    <Trash2 className="h-3.5 w-3.5" /> Remove
                  </Button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <Label className="label-uppercase mb-2 block">Procedure</Label>
                    <ProcedureSelect
                      value={row.procedure_code}
                      onChange={(v) => updateRow(idx, { procedure_code: v })}
                      procedures={procedures}
                      testid={`bulk-proc-select-${idx}`}
                    />
                  </div>
                  <div>
                    <Label className="label-uppercase mb-2 block">Tooth #</Label>
                    {proc && !proc.requires_tooth ? (
                      <Input value="N/A" disabled className="h-10" />
                    ) : (
                      <ToothPicker
                        value={row.tooth_number}
                        onChange={(v) => updateRow(idx, { tooth_number: v })}
                        triggerLabel="Pick tooth..."
                        testid={`bulk-tooth-${idx}`}
                      />
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <Label className="label-uppercase mb-2 block">Surfaces</Label>
                    <Input value={row.surfaces}
                      onChange={(e) => updateRow(idx, { surfaces: e.target.value })}
                      data-testid={`bulk-surfaces-${idx}`} placeholder="MOD" className="h-10" />
                  </div>
                  <div className="sm:col-span-2">
                    <Label className="label-uppercase mb-2 block">Clinical findings</Label>
                    <Input value={row.clinical_findings}
                      onChange={(e) => updateRow(idx, { clinical_findings: e.target.value })}
                      data-testid={`bulk-clinical-${idx}`}
                      placeholder="Fractured cusp, non-restorable caries..." className="h-10" />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <Label className="label-uppercase mb-2 block">Radiographic findings</Label>
                    <Input value={row.radiographic_findings}
                      onChange={(e) => updateRow(idx, { radiographic_findings: e.target.value })}
                      data-testid={`bulk-rads-${idx}`}
                      placeholder="Periapical radiolucency..." className="h-10" />
                  </div>
                  <div>
                    <Label className="label-uppercase mb-2 block">Notes</Label>
                    <Input value={row.additional_notes}
                      onChange={(e) => updateRow(idx, { additional_notes: e.target.value })}
                      data-testid={`bulk-notes-${idx}`}
                      placeholder="Optional" className="h-10" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-3 pt-4">
          <Button variant="outline" onClick={addRow} data-testid="bulk-add-row"
            className="rounded-full gap-1.5 h-11">
            <Plus className="h-4 w-4" /> Add another procedure
          </Button>
          <Button onClick={onGenerate} disabled={!canGenerate} data-testid="bulk-generate-btn"
            className="rounded-full h-11 px-6 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground gap-2 font-semibold">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {loading ? "Drafting..." : `Generate ${validRows.length || ""} narrative${validRows.length === 1 ? "" : "s"}`}
          </Button>
        </div>
      </section>

      <section className="xl:col-span-6 space-y-6" data-testid="bulk-output">
        {!visit && !loading && (
          <div className="clay p-10 text-center" data-testid="bulk-empty-state">
            <div className="w-14 h-14 mx-auto rounded-full bg-secondary grid place-items-center mb-4">
              <Sparkles className="h-6 w-6 text-[hsl(var(--primary))]" />
            </div>
            <div className="font-display font-bold text-xl">Add procedures to begin</div>
            <p className="text-muted-foreground text-sm mt-2 max-w-md mx-auto">
              Every procedure in the same visit shares the patient label, carrier, and visit notes.
              Generated packets download as one PDF.
            </p>
          </div>
        )}

        {visit && (
          <>
            <div className="clay p-5 flex items-center justify-between">
              <div>
                <div className="label-uppercase mb-1">Visit packet</div>
                <div className="font-display font-bold text-lg">
                  {visit.records.length} procedure{visit.records.length === 1 ? "" : "s"}
                  {visit.patient_label && <> · {visit.patient_label}</>}
                </div>
                <div className="text-xs text-muted-foreground mt-1 font-mono">
                  Carrier: {visit.carrier}
                  {visit.date_of_service && <> · {visit.date_of_service}</>}
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={onExportPdf}
                  data-testid="bulk-export-pdf" className="rounded-full gap-1.5">
                  <FileDown className="h-3.5 w-3.5" /> PDF packet
                </Button>
                <Button size="sm" variant="outline" onClick={onExportTxt}
                  data-testid="bulk-export-txt" className="rounded-full gap-1.5">
                  <FileText className="h-3.5 w-3.5" /> TXT
                </Button>
              </div>
            </div>

            {visit.records.map((rec, i) => (
              <div key={rec.id} className="space-y-4" data-testid={`bulk-record-${i}`}>
                <div className="clay p-4 flex items-center gap-3">
                  <span className="w-7 h-7 rounded-full bg-[hsl(var(--primary))] text-primary-foreground grid place-items-center font-mono text-xs font-bold">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-display font-bold text-base leading-tight truncate">
                      {rec.procedure_name}
                    </div>
                    <div className="text-xs text-muted-foreground font-mono">
                      CDT {rec.procedure_code}
                      {rec.tooth_number && ` · #${rec.tooth_number}`}
                    </div>
                  </div>
                </div>
                <NarrativeCard
                  label="Short"
                  testid={`bulk-short-${i}`}
                  text={rec.short_narrative}
                  subjectHint={`CDT ${rec.procedure_code} — ${rec.procedure_name}${rec.tooth_number ? ` · Tooth #${rec.tooth_number}` : ""}`}
                  onChange={(v) => onEditRecord(rec.id, "short_narrative", v)}
                />
                <NarrativeCard
                  label="Long"
                  testid={`bulk-long-${i}`}
                  text={rec.long_narrative}
                  subjectHint={`CDT ${rec.procedure_code} — ${rec.procedure_name}${rec.tooth_number ? ` · Tooth #${rec.tooth_number}` : ""}`}
                  onChange={(v) => onEditRecord(rec.id, "long_narrative", v)}
                />
                <RadiographPanel radiographs={rec.radiographs} />
              </div>
            ))}
          </>
        )}
      </section>
    </div>
  );
}
