// Deterministic color for a tag badge — same tag always renders the same
// color across the app, without needing a stored color per tag.
const TAG_PALETTE = [
  "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300",
  "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300",
  "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300",
  "bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900/40 dark:text-fuchsia-300",
  "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300",
];

// Well-known categories get a stable, hand-picked color so they read
// consistently even as the palette above evolves.
const KNOWN_TAG_COLORS: Record<string, string> = {
  invoice: TAG_PALETTE[0],
  contract: TAG_PALETTE[5],
  resume: TAG_PALETTE[6],
  tax: TAG_PALETTE[3],
  "purchase order": TAG_PALETTE[4],
  "medical record": TAG_PALETTE[2],
  "salary slip": TAG_PALETTE[7],
  "bank statement": TAG_PALETTE[1],
  receipt: TAG_PALETTE[0],
  letter: TAG_PALETTE[6],
};

function hashTag(tag: string): number {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = (hash * 31 + tag.charCodeAt(i)) >>> 0;
  }
  return hash;
}

export function tagColorClasses(tag: string): string {
  const key = tag.trim().toLowerCase();
  return KNOWN_TAG_COLORS[key] ?? TAG_PALETTE[hashTag(key) % TAG_PALETTE.length];
}
