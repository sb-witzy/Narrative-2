import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { Trash2, Search, FileDown, FileText, Copy, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  listAppeals, deleteAppeal, updateAppeal,
  exportAppealPdf, exportAppealTxt, apiErrorMessage,
} from "@/lib/api";

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  } catch { return iso; }
}

export default function Appeals() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    listAppeals()
      .then(setItems)
      .catch((e) => toast.error(apiErrorMessage(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = items.filter((it) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
      (it.subject_line || "").toLowerCase().includes(q) ||
      (it.procedure_code || "").toLowerCase().includes(q) ||
      (it.procedure_name || "").toLowerCase().includes(q) ||
      (it.carrier || "").toLowerCase().includes(q) ||
      (it.letter || "").toLowerCase().includes(q) ||
      (it.denial_reason || "").toLowerCase().includes(q)
    );
  });

  const openItem = (it) => {
    setSelected(it);
    setDraft(it.letter);
    setEditing(false);
  };

  const onDelete = async (id, e) => {
    if (e) e.stopPropagation();
    try {
      await deleteAppeal(id);
      setItems((prev) => prev.filter((x) => x.id !== id));
      if (selected?.id === id) setSelected(null);
      toast.success("Deleted");
    } catch (err) { toast.error(apiErrorMessage(err)); }
  };

  const onSave = async () => {
    if (!selected) return;
    try {
      const updated = await updateAppeal(selected.id, { letter: draft });
      setSelected(updated);
      setItems((prev) => prev.map((x) => x.id === updated.id ? updated : x));
      setEditing(false);
      toast.success("Letter saved");
    } catch (err) { toast.error(apiErrorMessage(err)); }
  };

  const onCopy = async () => {
    try { await navigator.clipboard.writeText(draft); toast.success("Copied"); }
    catch { toast.error("Copy failed"); }
  };

  const onPdf = async () => {
    if (!selected) return;
    try {
      await exportAppealPdf({ ...selected, letter: draft });
      toast.success("PDF downloaded");
    } catch (err) { toast.error(apiErrorMessage(err)); }
  };
  const onTxt = async () => {
    if (!selected) return;
    try {
      await exportAppealTxt({ ...selected, letter: draft });
      toast.success("Text downloaded");
    } catch (err) { toast.error(apiErrorMessage(err)); }
  };

  return (
    <div>
      <div className="flex items-end justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1 className="font-display font-black text-3xl sm:text-4xl tracking-tight">
            Appeal letters<span className="text-[hsl(var(--primary))]">.</span>
          </h1>
          <p className="text-muted-foreground mt-2 text-[15px]">
            {items.length} letter{items.length === 1 ? "" : "s"} drafted. Generate new ones from any saved narrative in History.
          </p>
        </div>
        <div className="relative w-full sm:w-80">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input data-testid="appeals-search" value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by code, carrier, reason..." className="pl-9 h-11" />
        </div>
      </div>

      {loading ? (
        <div className="clay p-10 text-center text-muted-foreground">Loading...</div>
      ) : filtered.length === 0 ? (
        <div className="clay p-10 text-center" data-testid="appeals-empty">
          <div className="font-display font-bold text-xl">
            {items.length === 0 ? "No appeal letters yet" : "No matches"}
          </div>
          <p className="text-muted-foreground text-sm mt-2 max-w-md mx-auto">
            {items.length === 0
              ? "Go to History, open any saved narrative, and click Draft appeal to generate a formal letter for a denied claim."
              : "Try a different search term."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((it) => (
            <div key={it.id} className="clay p-5 group cursor-pointer hover:-translate-y-0.5 transition-transform hover:shadow-md"
              onClick={() => openItem(it)}
              data-testid={`appeal-card-${it.id}`}>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    {it.procedure_code && (
                      <span className="font-mono text-xs bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] px-2 py-0.5 rounded">
                        {it.procedure_code}
                      </span>
                    )}
                    {it.tooth_number && (
                      <Badge variant="outline" className="rounded-full">#{it.tooth_number}</Badge>
                    )}
                    {it.carrier && it.carrier !== "generic" && (
                      <Badge className="rounded-full bg-secondary text-foreground hover:bg-secondary">
                        {it.carrier}
                      </Badge>
                    )}
                  </div>
                  <div className="font-display font-bold text-base mt-2 leading-snug truncate">
                    {it.subject_line}
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 group-hover:text-foreground transition-colors" />
              </div>
              <p className="text-sm text-foreground/80 line-clamp-2 leading-relaxed mt-2">
                <span className="text-muted-foreground">Denial: </span>
                {it.denial_reason}
              </p>
              <div className="flex items-center justify-between mt-4 pt-3 border-t border-border">
                <span className="text-xs text-muted-foreground">{formatDate(it.created_at)}</span>
                <div className="flex items-center gap-1">
                  <button onClick={(e) => { e.stopPropagation(); onDelete(it.id); }}
                    data-testid={`appeal-delete-${it.id}`}
                    className="text-muted-foreground hover:text-destructive p-1 rounded transition-colors">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="font-display text-xl">{selected.subject_line}</DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground">
                  {selected.procedure_code && `CDT ${selected.procedure_code} · `}
                  {selected.tooth_number && `Tooth #${selected.tooth_number} · `}
                  {selected.carrier && `${selected.carrier} · `}
                  {formatDate(selected.created_at)}
                </DialogDescription>
              </DialogHeader>

              <div className="flex flex-wrap gap-2 mt-3">
                <Button size="sm" variant="outline" onClick={onPdf}
                  data-testid="appeal-dlg-pdf" className="rounded-full gap-1.5">
                  <FileDown className="h-3.5 w-3.5" /> PDF
                </Button>
                <Button size="sm" variant="outline" onClick={onTxt}
                  data-testid="appeal-dlg-txt" className="rounded-full gap-1.5">
                  <FileText className="h-3.5 w-3.5" /> TXT
                </Button>
                <Button size="sm" variant="outline" onClick={onCopy}
                  data-testid="appeal-dlg-copy" className="rounded-full gap-1.5">
                  <Copy className="h-3.5 w-3.5" /> Copy
                </Button>
                <div className="ml-auto flex gap-2">
                  {!editing ? (
                    <Button size="sm" variant="ghost" onClick={() => setEditing(true)}
                      data-testid="appeal-dlg-edit" className="rounded-full">
                      Edit
                    </Button>
                  ) : (
                    <Button size="sm" onClick={onSave}
                      data-testid="appeal-dlg-save"
                      className="rounded-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground">
                      Save
                    </Button>
                  )}
                </div>
              </div>

              <div className="clay p-5 mt-4">
                <div className="label-uppercase mb-3">Denial reason</div>
                <p className="text-sm text-foreground/80 mb-4 bg-secondary/60 border border-border rounded-md p-3">
                  {selected.denial_reason}
                </p>
                <div className="label-uppercase mb-2">Letter</div>
                {editing ? (
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    data-testid="appeal-dlg-textarea"
                    rows={18}
                    className="w-full font-mono text-sm leading-relaxed rounded-md border border-input bg-background p-3 focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/50"
                  />
                ) : (
                  <pre className="whitespace-pre-wrap font-sans text-[15px] leading-relaxed text-foreground/90"
                       data-testid="appeal-dlg-letter">
                    {draft}
                  </pre>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
