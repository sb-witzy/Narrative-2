import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select";

const CATEGORY_ORDER = [
  "Crown", "Restorative", "Endodontics", "Extraction",
  "Periodontics", "Implant", "Bridge", "Surgical", "Occlusal Guard",
];

export function groupByCategory(procs) {
  const map = {};
  procs.forEach((p) => {
    map[p.category] = map[p.category] || [];
    map[p.category].push(p);
  });
  return CATEGORY_ORDER.filter((c) => map[c]).map((c) => ({ category: c, items: map[c] }));
}

export default function ProcedureSelect({ value, onChange, procedures, testid = "procedure-select" }) {
  const grouped = groupByCategory(procedures);
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger data-testid={testid} className="h-11 text-base">
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
                <span className="font-mono text-xs mr-2 text-[hsl(var(--primary))]">{p.code}</span>
                {p.name}
              </SelectItem>
            ))}
          </SelectGroup>
        ))}
      </SelectContent>
    </Select>
  );
}
