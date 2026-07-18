import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Copy, Loader2, RefreshCw, Check, Pencil, Printer, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { printLetter, emailLetter } from "@/lib/documentActions";

export default function NarrativeCard({
  label,
  testid,
  text,
  editable = true,
  onChange,
  onRegenerate,
  regenerating = false,
  subjectHint,
}) {
  const [editing, setEditing] = useState(false);
  const [flash, setFlash] = useState(false);
  const [localText, setLocalText] = useState(text || "");

  useEffect(() => {
    setLocalText(text || "");
  }, [text]);

  const wordCount = localText ? localText.trim().split(/\s+/).filter(Boolean).length : 0;

  const commit = () => {
    if (onChange) onChange(localText);
    setEditing(false);
  };

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(localText);
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
      <div className="flex items-center justify-between mb-3 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="label-uppercase">{label}</span>
          <span className="text-xs text-muted-foreground shrink-0">
            {wordCount} {wordCount === 1 ? "word" : "words"}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {editable && !editing && (
            <Button
              onClick={() => setEditing(true)}
              size="sm"
              variant="ghost"
              disabled={!localText}
              data-testid={`edit-${testid}`}
              className="gap-1.5 rounded-full h-8"
            >
              <Pencil className="h-3.5 w-3.5" /> Edit
            </Button>
          )}
          {editing && (
            <Button
              onClick={commit}
              size="sm"
              variant="ghost"
              data-testid={`save-${testid}`}
              className="gap-1.5 rounded-full h-8 text-[hsl(var(--primary))]"
            >
              <Check className="h-3.5 w-3.5" /> Save
            </Button>
          )}
          {onRegenerate && (
            <Button
              onClick={onRegenerate}
              size="sm"
              variant="ghost"
              disabled={regenerating}
              data-testid={`regenerate-${testid}`}
              className="gap-1.5 rounded-full h-8"
            >
              {regenerating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              Regenerate
            </Button>
          )}
          <Button
            onClick={onCopy}
            size="sm"
            variant="outline"
            disabled={!localText}
            data-testid={`copy-${testid}`}
            className="gap-1.5 rounded-full h-8"
          >
            <Copy className="h-3.5 w-3.5" /> Copy
          </Button>
          <Button
            onClick={() =>
              printLetter({
                title: subjectHint || label,
                subject: subjectHint || label,
                body: localText,
              })
            }
            size="sm"
            variant="ghost"
            disabled={!localText}
            data-testid={`print-${testid}`}
            className="gap-1.5 rounded-full h-8"
            title="Open printer dialog"
          >
            <Printer className="h-3.5 w-3.5" /> Print
          </Button>
          <Button
            onClick={() =>
              emailLetter({
                subject: subjectHint ? `${subjectHint} — ${label}` : label,
                body: localText,
              })
            }
            size="sm"
            variant="ghost"
            disabled={!localText}
            data-testid={`email-${testid}`}
            className="gap-1.5 rounded-full h-8"
            title="Open in email application"
          >
            <Mail className="h-3.5 w-3.5" /> Email
          </Button>
        </div>
      </div>
      {editing ? (
        <Textarea
          value={localText}
          onChange={(e) => setLocalText(e.target.value)}
          rows={label.toLowerCase().includes("long") ? 6 : 3}
          data-testid={`textarea-${testid}`}
          className="text-[15px] leading-relaxed"
          autoFocus
        />
      ) : (
        <p className="text-[15px] leading-relaxed whitespace-pre-wrap text-foreground/90 min-h-[3rem]">
          {localText || (
            <span className="text-muted-foreground italic">Not generated yet.</span>
          )}
        </p>
      )}
    </div>
  );
}
