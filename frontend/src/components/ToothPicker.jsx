import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { X } from "lucide-react";

// Universal Numbering System, patient-facing view (viewer's left = patient's right)
const ADULT_UPPER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];
const ADULT_LOWER = [32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17];
const PRIMARY_UPPER = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"];
const PRIMARY_LOWER = ["T", "S", "R", "Q", "P", "O", "N", "M", "L", "K"];

function ToothRow({ teeth, selected, onToggle, testidPrefix }) {
  return (
    <div className="flex gap-1 justify-center">
      {teeth.map((t) => {
        const isSel = selected.includes(String(t));
        return (
          <button
            key={t}
            type="button"
            onClick={() => onToggle(String(t))}
            data-testid={`${testidPrefix}-${t}`}
            className={`w-10 h-12 rounded-md text-sm font-mono font-semibold border transition-colors ${
              isSel
                ? "bg-[hsl(var(--primary))] text-primary-foreground border-[hsl(var(--primary))]"
                : "bg-card text-foreground border-border hover:border-[hsl(var(--primary))] hover:bg-secondary"
            }`}
          >
            {t}
          </button>
        );
      })}
    </div>
  );
}

export default function ToothPicker({
  value = "",
  onChange,
  multi = false,
  triggerLabel,
  testid = "tooth-picker",
}) {
  const [open, setOpen] = useState(false);
  const selected = value
    ? String(value)
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : [];

  const toggle = (t) => {
    let next;
    if (multi) {
      next = selected.includes(t)
        ? selected.filter((x) => x !== t)
        : [...selected, t];
    } else {
      next = selected[0] === t ? [] : [t];
    }
    const asString = next.join(", ");
    onChange(asString);
    if (!multi) setOpen(false);
  };

  const clear = () => {
    onChange("");
  };

  return (
    <div className="flex items-center gap-2">
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button
            type="button"
            variant="outline"
            data-testid={`${testid}-open`}
            className="h-10 w-full justify-start font-mono text-sm rounded-md"
          >
            {value || triggerLabel || "Select tooth..."}
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-[720px]">
          <DialogHeader>
            <DialogTitle className="font-display">
              {multi ? "Select teeth" : "Select tooth"}
            </DialogTitle>
            <DialogDescription>
              Universal Numbering System. Click a tooth to {multi ? "toggle" : "choose"} it.
            </DialogDescription>
          </DialogHeader>
          <Tabs defaultValue="adult">
            <TabsList className="grid grid-cols-2 w-fit">
              <TabsTrigger value="adult" data-testid={`${testid}-tab-adult`}>
                Adult (1–32)
              </TabsTrigger>
              <TabsTrigger value="primary" data-testid={`${testid}-tab-primary`}>
                Primary (A–T)
              </TabsTrigger>
            </TabsList>
            <TabsContent value="adult" className="mt-4">
              <div className="space-y-2 py-2">
                <div className="label-uppercase text-center">Upper (Maxillary)</div>
                <ToothRow
                  teeth={ADULT_UPPER}
                  selected={selected}
                  onToggle={toggle}
                  testidPrefix={`${testid}-tooth`}
                />
                <div className="h-px bg-border my-3" />
                <ToothRow
                  teeth={ADULT_LOWER}
                  selected={selected}
                  onToggle={toggle}
                  testidPrefix={`${testid}-tooth`}
                />
                <div className="label-uppercase text-center pt-1">Lower (Mandibular)</div>
              </div>
            </TabsContent>
            <TabsContent value="primary" className="mt-4">
              <div className="space-y-2 py-2">
                <div className="label-uppercase text-center">Upper (Maxillary)</div>
                <ToothRow
                  teeth={PRIMARY_UPPER}
                  selected={selected}
                  onToggle={toggle}
                  testidPrefix={`${testid}-tooth`}
                />
                <div className="h-px bg-border my-3" />
                <ToothRow
                  teeth={PRIMARY_LOWER}
                  selected={selected}
                  onToggle={toggle}
                  testidPrefix={`${testid}-tooth`}
                />
                <div className="label-uppercase text-center pt-1">Lower (Mandibular)</div>
              </div>
            </TabsContent>
          </Tabs>
          <div className="flex items-center justify-between pt-4 border-t border-border mt-4">
            <div className="text-sm text-muted-foreground">
              {selected.length
                ? `Selected: ${selected.join(", ")}`
                : "No teeth selected"}
            </div>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                onClick={clear}
                data-testid={`${testid}-clear`}
                className="rounded-full"
              >
                Clear
              </Button>
              <Button
                onClick={() => setOpen(false)}
                data-testid={`${testid}-done`}
                className="rounded-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90 text-primary-foreground"
              >
                Done
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      {value && (
        <button
          type="button"
          onClick={clear}
          data-testid={`${testid}-quick-clear`}
          className="text-muted-foreground hover:text-foreground p-1 rounded"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
