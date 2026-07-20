import { useState, useEffect } from "react";
import { toast } from "sonner";
import {
  Loader2, Sparkles, Copy, FileDown, FileText, ArrowLeft, RefreshCw,
  Printer, Mail, Trophy, XCircle, Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  streamAppeal, makeMarkerParser, updateAppeal, setAppealOutcome,
  getAppealPatterns, exportAppealPdf, exportAppealTxt, apiErrorMessage,
} from "@/lib/api";
import { printLetter, emailLetter, copyText } from "@/lib/documentActions";

const OUTCOME_META = {
  pending: { label: "Pending", cls: "bg-amber-100 text-amber-800 border border-amber-200", Icon: Clock },
  won:     { label: "Won",     cls: "bg-emerald-100 text-emerald-800 border border-emerald-200", Icon: Trophy },
  lost:    { label: "Lost",    cls: "bg-rose-100 text-rose-800 border border-rose-200", Icon: XCircle },
};

export default function AppealDialog({ open, onOpenChange, narrative }) {
  const [denialReason, setDenialReason] = useState("");
  const [denialCode, setDenialCode] = useState("");
  const [extraContext, setExtraContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [appeal, setAppeal] = useState(null);
  const [editing, setEditing] = useState(false);
  const [localLetter, setLocalLetter] = useState("");
  const [localSubject, setLocalSubject] = useState("");
  const [patterns, setPatterns] = useState(null);
  const [outcomeNotes, setOutcomeNotes] = useState("");
  const [outcomeLoading, setOutcomeLoading] = useState(false);

  const reset = () => {
    setDenialReason(""); setDenialCode(""); setExtraContext("");
    setAppeal(null); setEditing(false);
    setLocalLetter(""); setLocalSubject("");
    setPatterns(null); setOutcomeNotes("");
  };
  const onClose = (v) => { if (!v) reset(); onOpenChange(v); };

  // Fetch carrier + procedure patterns as soon as the dialog opens
  useEffect(() => {
    if (!open || !narrative) return;
    getAppealPatterns(narrative.carrier, narrative.procedure_code)
      .then(setPatterns)
      .catch(() => setPatterns(null));
  }, [open, narrative]);

  const onGenerate = async () => {
    if (!narrative || !denialReason.trim()) {
      toast.error("Denial reason is required");
      return;
    }
    setLoading(true);
    setAppeal({ subject_line: "", letter: "", _streaming: true });
    setLocalSubject(""); setLocalLetter("");
    const parser = makeMarkerParser();
    await streamAppeal(
      {
        narrative_id: narrative.id,
        denial_reason: denialReason,
        denial_code: denialCode || undefined,
        extra_context: extraContext || undefined,
      },
      {
        onChunk: (text) => {
          parser.feed(text);
          setLocalSubject(parser.state.subject);
          setLocalLetter(parser.state.letter);
        },
        onDone: (record) => {
          setAppeal({ ...record, _streaming: false });
          setLocalSubject(record.subject_line || "");
          setLocalLetter(record.letter || "");
          setOutcomeNotes(record.outcome_notes || "");
          toast.success("Appeal letter generated");
          setLoading(false);
        },
        onError: (err) => {
          toast.error(err?.message || "Generation failed. Please retry.");
          setAppeal(null);
          setLoading(false);
        },
      }
    );
  };

  const onRegenerate = async () => {
    setAppeal(null);
    await onGenerate();
  };

  const onSaveEdit = async () => {
    if (!appeal?.id) return;
    try {
      const updated = await updateAppeal(appeal.id, {
        letter: localLetter, subject_line: localSubject,
      });
      setAppeal(updated);
      setEditing(false);
      toast.success("Letter saved");
    } catch (err) { toast.error(apiErrorMessage(err)); }
  };

  const onCopy = async () => {
    const ok = await copyText(localLetter);
    if (ok) toast.success("Letter copied to clipboard");
    else toast.error("Copy failed - select the text manually with Ctrl+A, Ctrl+C");
  };

  const onPdf = async () => {
    if (!appeal?.id) return;
    try { await exportAppealPdf({ ...appeal, letter: localLetter, subject_line: localSubject }); toast.success("Appeal PDF downloaded"); }
    catch (err) { toast.error(apiErrorMessage(err)); }
  };

  const onTxt = async () => {
    if (!appeal?.id) return;
    try { await exportAppealTxt({ ...appeal, letter: localLetter, subject_line: localSubject }); toast.success("Appeal text downloaded"); }
    catch (err) { toast.error(apiErrorMessage(err)); }
  };

  const onMarkOutcome = async (outcome) => {
    if (!appeal?.id) return;
    setOutcomeLoading(true);
    try {
      const updated = await setAppealOutcome(appeal.id, outcome, outcomeNotes || undefined);
      setAppeal(updated);
      toast.success(`Appeal marked as ${OUTCOME_META[outcome].label}`);
    } catch (err) { toast.error(apiErrorMessage(err)); }
    finally { setOutcomeLoading(false); }
  };

  const currentOutcome = appeal?.outcome || "pending";
  const outcomeMeta = OUTCOME_META[currentOutcome] || OUTCOME_META.pending;
  const OutcomeIcon = outcomeMeta.Icon;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="appeal-dialog">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl">
            {appeal ? "Appeal letter draft" : "Draft appeal letter"}
          </DialogTitle>
          <DialogDescription>
            {narrative && (
              <>
                <span className="font-mono text-[hsl(var(--primary))]">{narrative.procedure_code}</span>{" "}
                {narrative.procedure_name}
                {narrative.tooth_number && ` · Tooth #${narrative.tooth_number}`}
                {narrative.carrier && narrative.carrier !== "generic" && ` · ${narrative.carrier}`}
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        {/* Prior appeal patterns for this carrier + procedure */}
        {!appeal && patterns && patterns.total > 0 && (
          <div className="rounded-xl border border-border bg-secondary/40 p-4" data-testid="appeal-patterns">
            <div className="flex items-center gap-2 mb-2">
              <Trophy className="h-4 w-4 text-[hsl(var(--primary))]" />
              <span className="label-uppercase">Your track record with this carrier + procedure</span>
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              <Badge className="bg-emerald-100 text-emerald-800 border border-emerald-200 hover:bg-emerald-100">
                {patterns.won} won
              </Badge>
              <Badge className="bg-rose-100 text-rose-800 border border-rose-200 hover:bg-rose-100">
                {patterns.lost} lost
              </Badge>
              <Badge className="bg-amber-100 text-amber-800 border border-amber-200 hover:bg-amber-100">
                {patterns.pending} pending
              </Badge>
              {patterns.win_rate != null && (
                <span className="text-muted-foreground">
                  · Win rate: <span className="font-semibold text-foreground">{Math.round(patterns.win_rate * 100)}%</span>
                </span>
              )}
            </div>
            {patterns.winning_appeals?.length > 0 && (
              <p className="text-xs text-muted-foreground mt-2">
                The AI will reference your {patterns.winning_appeals.length} most recent winning appeal{patterns.winning_appeals.length > 1 ? "s" : ""}
                {" "}to match your practice's proven arguments.
              </p>
            )}
          </div>
        )}

        {!appeal ? (
          <div className="space-y-5 mt-2" data-testid="appeal-input-form">
            <div>
              <Label className="label-uppercase mb-2 block">
                Carrier denial reason <span className="text-destructive normal-case tracking-normal">*</span>
              </Label>
              <Textarea
                rows={3} value={denialReason} onChange={(e) => setDenialReason(e.target.value)}
                data-testid="appeal-denial-reason"
                placeholder="E.g., Not medically necessary. Insufficient documentation to establish that a less costly alternative was ruled out."
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="label-uppercase mb-2 block">Denial code</Label>
                <Input
                  value={denialCode} onChange={(e) => setDenialCode(e.target.value)}
                  data-testid="appeal-denial-code"
                  placeholder="Optional — e.g., D-501" className="h-10"
                />
              </div>
              <div className="flex items-end">
                <Button
                  onClick={onGenerate} disabled={loading || !denialReason.trim()}
                  data-testid="appeal-generate-btn"
                  className="w-full h-11 rounded-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground gap-2 font-semibold"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {loading ? "Drafting..." : "Generate letter"}
                </Button>
              </div>
            </div>
            <div>
              <Label className="label-uppercase mb-2 block">Additional context (optional)</Label>
              <Textarea
                rows={3} value={extraContext} onChange={(e) => setExtraContext(e.target.value)}
                data-testid="appeal-extra-context"
                placeholder="Any extra facts to help the appeal — prior authorization number, additional radiographs enclosed, previous treatment attempts, etc."
              />
            </div>
          </div>
        ) : (
          <div className="space-y-4 mt-2" data-testid="appeal-result">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge className="bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/10 rounded-full">
                Subject
              </Badge>
              <span className="text-sm font-medium">{localSubject || appeal.subject_line}</span>
              {appeal.id && (
                <Badge className={`rounded-full ml-auto ${outcomeMeta.cls}`} data-testid="appeal-outcome-badge">
                  <OutcomeIcon className="h-3 w-3 mr-1" />
                  {outcomeMeta.label}
                </Badge>
              )}
            </div>

            <div className="clay p-5 relative">
              <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
                <span className="label-uppercase">Appeal letter</span>
                <div className="flex gap-1.5 flex-wrap">
                  {appeal.id && !editing && (
                    <Button size="sm" variant="ghost" onClick={() => setEditing(true)}
                      data-testid="appeal-edit-btn" className="rounded-full h-8">
                      Edit
                    </Button>
                  )}
                  {editing && (
                    <Button size="sm" variant="ghost" onClick={onSaveEdit}
                      data-testid="appeal-save-btn"
                      className="rounded-full h-8 text-[hsl(var(--primary))]">
                      Save
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={onRegenerate}
                    disabled={loading}
                    data-testid="appeal-regenerate-btn"
                    className="rounded-full h-8 gap-1.5">
                    {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                    Regenerate
                  </Button>
                  <Button size="sm" variant="outline" onClick={onCopy}
                    disabled={!localLetter}
                    data-testid="appeal-copy-btn" className="rounded-full h-8 gap-1.5">
                    <Copy className="h-3.5 w-3.5" /> Copy
                  </Button>
                </div>
              </div>
              {editing ? (
                <Textarea
                  value={localLetter} onChange={(e) => setLocalLetter(e.target.value)}
                  rows={16} data-testid="appeal-letter-textarea"
                  className="font-mono text-sm leading-relaxed"
                />
              ) : (
                <pre className="whitespace-pre-wrap font-sans text-[15px] leading-relaxed text-foreground/90"
                     data-testid="appeal-letter-text">
                  {localLetter}
                  {appeal._streaming && <span className="inline-block w-2 h-4 bg-[hsl(var(--primary))]/60 animate-pulse ml-0.5 align-middle" />}
                </pre>
              )}
            </div>

            {/* Outcome tracker — only after save */}
            {appeal.id && (
              <div className="rounded-xl border border-border p-4 space-y-3" data-testid="appeal-outcome-section">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <div className="label-uppercase">Track this appeal</div>
                    <p className="text-xs text-muted-foreground mt-1">
                      When you hear back from the carrier, mark the outcome. Wins train the AI to draft better future appeals.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant={currentOutcome === "won" ? "default" : "outline"}
                      onClick={() => onMarkOutcome("won")} disabled={outcomeLoading}
                      data-testid="appeal-mark-won"
                      className={`rounded-full h-9 gap-1.5 ${currentOutcome === "won" ? "bg-emerald-600 hover:bg-emerald-700 text-white" : ""}`}>
                      <Trophy className="h-3.5 w-3.5" /> Won
                    </Button>
                    <Button size="sm" variant={currentOutcome === "lost" ? "default" : "outline"}
                      onClick={() => onMarkOutcome("lost")} disabled={outcomeLoading}
                      data-testid="appeal-mark-lost"
                      className={`rounded-full h-9 gap-1.5 ${currentOutcome === "lost" ? "bg-rose-600 hover:bg-rose-700 text-white" : ""}`}>
                      <XCircle className="h-3.5 w-3.5" /> Lost
                    </Button>
                    <Button size="sm" variant={currentOutcome === "pending" ? "default" : "outline"}
                      onClick={() => onMarkOutcome("pending")} disabled={outcomeLoading}
                      data-testid="appeal-mark-pending"
                      className={`rounded-full h-9 gap-1.5 ${currentOutcome === "pending" ? "bg-amber-500 hover:bg-amber-600 text-white" : ""}`}>
                      <Clock className="h-3.5 w-3.5" /> Pending
                    </Button>
                  </div>
                </div>
                <Textarea
                  value={outcomeNotes} onChange={(e) => setOutcomeNotes(e.target.value)}
                  rows={2} data-testid="appeal-outcome-notes"
                  placeholder="Optional notes — e.g. carrier's response, amount paid, requested more info, resubmit date"
                  className="text-sm"
                />
              </div>
            )}

            <div className="flex items-center justify-between pt-2 flex-wrap gap-2">
              <Button variant="ghost" onClick={() => { setAppeal(null); setLocalLetter(""); setLocalSubject(""); }}
                data-testid="appeal-back-btn" className="gap-1.5 rounded-full">
                <ArrowLeft className="h-4 w-4" /> Change inputs
              </Button>
              <div className="flex gap-2 flex-wrap">
                <Button size="sm" variant="outline" disabled={!localLetter}
                  onClick={() => printLetter({ title: localSubject || appeal.subject_line || "Appeal letter", subject: localSubject || appeal.subject_line, body: localLetter })}
                  data-testid="appeal-print-btn" className="rounded-full gap-1.5">
                  <Printer className="h-3.5 w-3.5" /> Print
                </Button>
                <Button size="sm" variant="outline" disabled={!localLetter}
                  onClick={() => emailLetter({ subject: localSubject || appeal.subject_line || "Appeal letter", body: localLetter })}
                  data-testid="appeal-email-btn" className="rounded-full gap-1.5">
                  <Mail className="h-3.5 w-3.5" /> Email
                </Button>
                <Button size="sm" variant="outline" onClick={onPdf} disabled={!appeal.id}
                  data-testid="appeal-export-pdf" className="rounded-full gap-1.5">
                  <FileDown className="h-3.5 w-3.5" /> PDF
                </Button>
                <Button size="sm" variant="outline" onClick={onTxt} disabled={!appeal.id}
                  data-testid="appeal-export-txt" className="rounded-full gap-1.5">
                  <FileText className="h-3.5 w-3.5" /> TXT
                </Button>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
