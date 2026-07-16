import { Camera, Info, Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function RadiographPanel({ radiographs }) {
  if (!radiographs) return null;
  const { required = [], recommended = [], note = "" } = radiographs;
  return (
    <div className="clay p-6" data-testid="radiograph-panel">
      <div className="flex items-center gap-2 mb-4">
        <Camera className="h-4 w-4 text-[hsl(var(--primary))]" />
        <span className="label-uppercase">Radiographs to submit</span>
      </div>
      {required.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-semibold text-foreground/80 mb-2">Required</div>
          <div className="flex flex-wrap gap-2">
            {required.map((r) => (
              <Badge
                key={r}
                data-testid={`xray-required-${r}`}
                className="bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-primary-foreground rounded-full px-3 py-1"
              >
                <Check className="h-3 w-3 mr-1" /> {r}
              </Badge>
            ))}
          </div>
        </div>
      )}
      {recommended.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-semibold text-foreground/80 mb-2">Recommended</div>
          <div className="flex flex-wrap gap-2">
            {recommended.map((r) => (
              <Badge
                key={r}
                variant="outline"
                data-testid={`xray-recommended-${r}`}
                className="rounded-full px-3 py-1 border-[hsl(var(--warning))] text-[hsl(var(--warning))]"
              >
                {r}
              </Badge>
            ))}
          </div>
        </div>
      )}
      {required.length === 0 && recommended.length === 0 && (
        <div className="text-sm text-muted-foreground">
          No radiographs typically required for this procedure.
        </div>
      )}
      {note && (
        <div className="mt-4 text-sm text-foreground/80 bg-secondary/60 rounded-md p-3 border border-border flex gap-2">
          <Info className="h-4 w-4 mt-0.5 shrink-0 text-[hsl(var(--primary))]" />
          <span>{note}</span>
        </div>
      )}
    </div>
  );
}
