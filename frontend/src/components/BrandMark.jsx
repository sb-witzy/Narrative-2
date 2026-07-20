// Shared Narrative.Rx brand mark.
// Uses the pre-built /logo512.png (a 512x512 PNG generated from the master .ico).
// The icon already contains the "Narrative.Rx" wordmark, so we don't repeat it as text.
// The optional `tagline` prop shows a small secondary label to the right (nav / auth headers).

export default function BrandMark({ size = 40, tagline, className = "" }) {
  const px = `${size}px`;
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src="/logo512.png"
        alt="Narrative.Rx"
        width={size}
        height={size}
        style={{ width: px, height: px }}
        className="rounded-[22%] shadow-sm ring-1 ring-black/5 select-none"
        draggable={false}
      />
      {tagline ? (
        <div className="label-uppercase leading-tight text-muted-foreground">{tagline}</div>
      ) : null}
    </div>
  );
}
