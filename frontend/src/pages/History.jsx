import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Copy, Trash2, ChevronRight, Search, Camera, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { listHistory, deleteHistoryItem } from "@/lib/api";

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function copy(text, label = "Copied") {
  navigator.clipboard
    .writeText(text)
    .then(() => toast.success(`${label} copied`))
    .catch(() => toast.error("Copy failed"));
}

export default function History() {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    listHistory()
      .then(setItems)
      .catch(() => toast.error("Failed to load history"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = items.filter((it) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
      it.procedure_code.toLowerCase().includes(q) ||
      it.procedure_name.toLowerCase().includes(q) ||
      (it.tooth_number || "").toLowerCase().includes(q) ||
      (it.patient_label || "").toLowerCase().includes(q) ||
      it.short_narrative.toLowerCase().includes(q)
    );
  });

  const onDelete = async (id, e) => {
    e.stopPropagation();
    try {
      await deleteHistoryItem(id);
      setItems((prev) => prev.filter((x) => x.id !== id));
      toast.success("Deleted");
      if (selected?.id === id) setSelected(null);
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <div>
      <div className="flex items-end justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1 className="font-display font-black text-3xl sm:text-4xl tracking-tight">
            Saved narratives
            <span className="text-[hsl(var(--primary))]">.</span>
          </h1>
          <p className="text-muted-foreground mt-2 text-[15px]">
            {items.length} record{items.length === 1 ? "" : "s"} saved.
          </p>
        </div>
        <div className="relative w-full sm:w-80">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            data-testid="history-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by code, tooth, patient..."
            className="pl-9 h-11"
          />
        </div>
      </div>

      {loading ? (
        <div className="clay p-10 text-center text-muted-foreground">
          Loading...
        </div>
      ) : filtered.length === 0 ? (
        <div className="clay p-10 text-center" data-testid="history-empty">
          <div className="font-display font-bold text-xl">
            {items.length === 0 ? "No saved narratives yet" : "No matches"}
          </div>
          <p className="text-muted-foreground text-sm mt-2">
            {items.length === 0
              ? "Generate one from the dashboard — they'll appear here automatically."
              : "Try a different search term."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((it) => (
            <button
              key={it.id}
              onClick={() => setSelected(it)}
              data-testid={`history-item-${it.id}`}
              className="clay p-5 text-left hover:-translate-y-0.5 transition-transform hover:shadow-md group"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] px-2 py-0.5 rounded">
                      {it.procedure_code}
                    </span>
                    {it.tooth_number && (
                      <Badge variant="outline" className="rounded-full">
                        #{it.tooth_number}
                      </Badge>
                    )}
                  </div>
                  <div className="font-display font-bold text-base mt-1.5 leading-snug">
                    {it.procedure_name}
                  </div>
                  {it.patient_label && (
                    <div className="text-xs text-muted-foreground mt-1">
                      {it.patient_label}
                    </div>
                  )}
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 group-hover:text-foreground transition-colors" />
              </div>
              <p className="text-sm text-foreground/80 line-clamp-3 leading-relaxed">
                {it.short_narrative}
              </p>
              <div className="flex items-center justify-between mt-4 pt-3 border-t border-border">
                <span className="text-xs text-muted-foreground">
                  {formatDate(it.created_at)}
                </span>
                <span
                  onClick={(e) => onDelete(it.id, e)}
                  data-testid={`delete-${it.id}`}
                  className="text-muted-foreground hover:text-destructive p-1 rounded transition-colors cursor-pointer"
                  role="button"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="font-display text-2xl">
                  <span className="font-mono text-sm text-[hsl(var(--primary))] mr-2">
                    {selected.procedure_code}
                  </span>
                  {selected.procedure_name}
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground mt-1">
                  {selected.tooth_number && `Tooth #${selected.tooth_number} · `}
                  {selected.patient_label && `${selected.patient_label} · `}
                  {formatDate(selected.created_at)}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-5 mt-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="label-uppercase">Short narrative</span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        copy(selected.short_narrative, "Short narrative")
                      }
                      data-testid="dlg-copy-short"
                      className="rounded-full gap-1.5"
                    >
                      <Copy className="h-3.5 w-3.5" /> Copy
                    </Button>
                  </div>
                  <p className="text-[15px] leading-relaxed bg-secondary/50 border border-border rounded-lg p-4">
                    {selected.short_narrative}
                  </p>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="label-uppercase">Long narrative</span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        copy(selected.long_narrative, "Long narrative")
                      }
                      data-testid="dlg-copy-long"
                      className="rounded-full gap-1.5"
                    >
                      <Copy className="h-3.5 w-3.5" /> Copy
                    </Button>
                  </div>
                  <p className="text-[15px] leading-relaxed bg-secondary/50 border border-border rounded-lg p-4 whitespace-pre-wrap">
                    {selected.long_narrative}
                  </p>
                </div>

                {selected.radiographs && (
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Camera className="h-4 w-4 text-[hsl(var(--primary))]" />
                      <span className="label-uppercase">Radiographs</span>
                    </div>
                    {selected.radiographs.required?.length > 0 && (
                      <div className="mb-2">
                        <div className="text-xs font-semibold mb-1.5">Required</div>
                        <div className="flex flex-wrap gap-2">
                          {selected.radiographs.required.map((r) => (
                            <Badge
                              key={r}
                              className="bg-[hsl(var(--primary))] text-primary-foreground rounded-full"
                            >
                              <Check className="h-3 w-3 mr-1" />
                              {r}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {selected.radiographs.recommended?.length > 0 && (
                      <div className="mb-2">
                        <div className="text-xs font-semibold mb-1.5">
                          Recommended
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {selected.radiographs.recommended.map((r) => (
                            <Badge
                              key={r}
                              variant="outline"
                              className="rounded-full"
                            >
                              {r}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {selected.radiographs.note && (
                      <p className="text-sm text-muted-foreground mt-2">
                        {selected.radiographs.note}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
