import { useState } from "react";
import { toast } from "sonner";
import { Loader2, Sparkles, Copy, FileDown, FileText, ArrowLeft, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  createAppeal, updateAppeal, exportAppealPdf, exportAppealTxt, apiErrorMessage,
} from "@/lib/api";

export default function AppealDialog({ open, onOpenChange, narrative }) {
  const [denialReason, setDenialReason] = useState("");
  const [denialCode, setDenialCode] = useState("");
  const [extraContext, setExtraContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [appeal, setAppeal] = useState(null);
  const [editing, setEditing] = useState(false);
  const [localLetter, setLocalLetter] = useState("");

  const reset = () => {
    setDenialReason("");
    setDenialCode("");
    setExtraContext("");
    setAppeal(null);
    setEditing(false);
    setLocalLetter("");
  };

  const onClose = (v) => {
    if (!v) reset();
    onOpenChange(v);
  };

  const onGenerate = async () => {
    if (!narrative || !denialReason.trim()) {
      toast.error("Denial reason is required");
      return;
    }
    setLoading(true);
    try {
      const data = await createAppeal({
        narrative_id: narrative.id,
        denial_reason: denialReason,
        denial_code: denialCode || undefined,
        extra_context: extraContext || undefined,
      });
      setAppeal(data);
      setLocalLetter(data.letter);
      toast.success("Appeal letter generated");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const onRegenerate = async () => {
    setAppeal(null);
    await onGenerate();
  };

  const onSaveEdit = async () => {
    if (!appeal) return;
    try {
      const updated = await updateAppeal(appeal.id, { letter: localLetter });
      setAppeal(updated);
      setEditing(false);
      toast.success("Letter saved");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(localLetter);
      toast.success("Letter copied to clipboard");
    } catch {
      toast.error("Copy failed");
    }
  };

  const onPdf = async () => {
    if (!appeal) return;
    try {
      await exportAppealPdf({ ...appeal, letter: localLetter });
      toast.success("Appeal PDF downloaded");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  const onTxt = async () => {
    if (!appeal) return;
    try {
      await exportAppealTxt({ ...appeal, letter: localLetter });
      toast.success("Appeal text downloaded");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

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
                <span className="font-mono text-[hsl(var(--primary))]">
                  {narrative.procedure_code}
                </span>{" "}
                {narrative.procedure_name}
                {narrative.tooth_number && ` · Tooth #${narrative.tooth_number}`}
                {narrative.carrier && narrative.carrier !== "generic" && ` · ${narrative.carrier}`}
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        {!appeal ? (
          <div className="space-y-5 mt-2" data-testid="appeal-input-form">
            <div>
              <Label className="label-uppercase mb-2 block">
                Carrier denial reason <span className="text-destructive normal-case tracking-normal">*</span>
              </Label>
              <Textarea
                rows={3}
                value={denialReason}
                onChange={(e) => setDenialReason(e.target.value)}
                data-testid="appeal-denial-reason"
                placeholder="E.g., Not medically necessary. Insufficient documentation to establish that a less costly alternative was ruled out."
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="label-uppercase mb-2 block">Denial code</Label>
                <Input
                  value={denialCode}
                  onChange={(e) => setDenialCode(e.target.value)}
                  data-testid="appeal-denial-code"
                  placeholder="Optional — e.g., D-501"
                  className="h-10"
                />
              </div>
              <div className="flex items-end">
                <Button
                  onClick={onGenerate}
                  disabled={loading || !denialReason.trim()}
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
                rows={3}
                value={extraContext}
                onChange={(e) => setExtraContext(e.target.value)}
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
              <span className="text-sm font-medium">{appeal.subject_line}</span>
            </div>

            <div className="clay p-5 relative">
              <div className="flex items-center justify-between mb-3 gap-2">
                <span className="label-uppercase">Appeal letter</span>
                <div className="flex gap-1.5">
                  {!editing ? (
                    <Button size="sm" variant="ghost" onClick={() => setEditing(true)}
                      data-testid="appeal-edit-btn" className="rounded-full h-8">
                      Edit
                    </Button>
                  ) : (
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
                    data-testid="appeal-copy-btn" className="rounded-full h-8 gap-1.5">
                    <Copy className="h-3.5 w-3.5" /> Copy
                  </Button>
                </div>
              </div>
              {editing ? (
                <Textarea
                  value={localLetter}
                  onChange={(e) => setLocalLetter(e.target.value)}
                  rows={16}
                  data-testid="appeal-letter-textarea"
                  className="font-mono text-sm leading-relaxed"
                />
              ) : (
                <pre className="whitespace-pre-wrap font-sans text-[15px] leading-relaxed text-foreground/90"
                     data-testid="appeal-letter-text">
                  {localLetter}
                </pre>
              )}
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button variant="ghost" onClick={() => { setAppeal(null); setLocalLetter(""); }}
                data-testid="appeal-back-btn" className="gap-1.5 rounded-full">
                <ArrowLeft className="h-4 w-4" /> Change inputs
              </Button>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={onPdf}
                  data-testid="appeal-export-pdf" className="rounded-full gap-1.5">
                  <FileDown className="h-3.5 w-3.5" /> PDF
                </Button>
                <Button size="sm" variant="outline" onClick={onTxt}
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
