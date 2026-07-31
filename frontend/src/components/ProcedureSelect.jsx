import { useState, useMemo } from "react";
import { Check, ChevronsUpDown, Search } from "lucide-react";
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Rendering order — keeps the dropdown organised by CDT range.
const CATEGORY_ORDER = [
  "Diagnostic",
  "Preventive",
  "Restorative",
  "Crown",
  "Endodontics",
  "Periodontics",
  "Extraction",
  "Bone Graft",
  "Implant",
  "Bridge",
  "Removable Prosthodontics",
  "Occlusal Guard",
];

export function groupByCategory(procs) {
  const map = {};
  procs.forEach((p) => {
    map[p.category] = map[p.category] || [];
    map[p.category].push(p);
  });
  // Categories not listed in CATEGORY_ORDER go to the end alphabetically
  const known = CATEGORY_ORDER.filter((c) => map[c]);
  const unknown = Object.keys(map).filter((c) => !CATEGORY_ORDER.includes(c)).sort();
  return [...known, ...unknown].map((c) => ({ category: c, items: map[c] }));
}

export default function ProcedureSelect({ value, onChange, procedures, testid = "procedure-select" }) {
  const [open, setOpen] = useState(false);

  const grouped = useMemo(() => groupByCategory(procedures), [procedures]);
  const selected = useMemo(
    () => procedures.find((p) => p.code === value),
    [procedures, value]
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          data-testid={testid}
          className="w-full h-11 justify-between text-base font-normal"
        >
          {selected ? (
            <span className="flex items-center gap-2 min-w-0">
              <span className="font-mono text-xs text-[hsl(var(--primary))] shrink-0">{selected.code}</span>
              <span className="truncate">{selected.name}</span>
            </span>
          ) : (
            <span className="text-muted-foreground">Select CDT code / procedure...</span>
          )}
          <ChevronsUpDown className="h-4 w-4 opacity-50 shrink-0 ml-2" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="p-0 w-[var(--radix-popover-trigger-width)]"
        align="start"
        data-testid={`${testid}-popover`}
      >
        <Command
          filter={(v, search) => {
            // v is the CommandItem's `value` (we set it to `<code> <name>` below)
            const s = search.toLowerCase().trim();
            if (!s) return 1;
            return v.toLowerCase().includes(s) ? 1 : 0;
          }}
        >
          <div className="flex items-center border-b px-3">
            <Search className="h-4 w-4 shrink-0 opacity-50 mr-2" />
            <CommandInput
              placeholder="Search by code or name (e.g. D5213 or partial denture)"
              className="h-11 border-0 focus:ring-0 focus-visible:ring-0"
              data-testid={`${testid}-search`}
            />
          </div>
          <CommandList className="max-h-[360px]">
            <CommandEmpty>No procedures match your search.</CommandEmpty>
            {grouped.map((g) => (
              <CommandGroup key={g.category} heading={g.category}>
                {g.items.map((p) => (
                  <CommandItem
                    key={p.code}
                    value={`${p.code} ${p.name}`}
                    onSelect={() => { onChange(p.code); setOpen(false); }}
                    data-testid={`procedure-option-${p.code}`}
                    className="cursor-pointer"
                  >
                    <Check
                      className={cn(
                        "h-4 w-4 mr-2 shrink-0",
                        value === p.code ? "opacity-100 text-[hsl(var(--primary))]" : "opacity-0"
                      )}
                    />
                    <span className="font-mono text-xs mr-2 text-[hsl(var(--primary))]">{p.code}</span>
                    <span className="truncate">{p.name}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
