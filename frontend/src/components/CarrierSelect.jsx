import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function CarrierSelect({ value, onChange, carriers, testid = "carrier-select" }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger data-testid={testid} className="h-10">
        <SelectValue placeholder="Carrier..." />
      </SelectTrigger>
      <SelectContent>
        {carriers.map((c) => (
          <SelectItem key={c.key} value={c.key} data-testid={`carrier-option-${c.key}`}>
            {c.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
