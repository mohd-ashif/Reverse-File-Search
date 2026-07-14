/**
 * Mirrors backend/app/services/folder_path_guard.py exactly. Keep the two in
 * sync — this drives the instant-while-typing risk badge; the backend is the
 * source of truth for actually blocking High-risk paths on submit.
 */

export type RiskLevel = "low" | "medium" | "high";

export interface RiskAssessment {
  level: RiskLevel;
  reason: string;
  recommendation: string;
}

export const FOLDER_TOO_BROAD_MESSAGE =
  "This folder is too broad and may expose sensitive system or personal files. " +
  "Please select a specific subfolder instead.";

export const RECOMMENDATION_HIGH = "Select a smaller, business-specific folder instead.";
export const RECOMMENDATION_MEDIUM = "Consider selecting a more specific subfolder, e.g. Documents\\Reports.";
export const RECOMMENDATION_LOW = "This folder looks safe to monitor.";

const MEDIUM_REASON = "This is a broad personal folder that likely mixes personal and business files.";
const LOW_REASON = "This looks like a specific, business-relevant folder.";

const HIGH_PATTERNS: Array<{ pattern: RegExp; reason: string }> = [
  { pattern: /^[A-Za-z]:[\\/]?$/, reason: "This is an entire drive, containing every file on the disk." },
  {
    pattern: /^[A-Za-z]:[\\/](Windows|Program Files( \(x86\))?|ProgramData)[\\/]?$/i,
    reason: "This is a Windows system directory required for the computer to function.",
  },
  {
    pattern: /^[A-Za-z]:[\\/]Users[\\/]?$/i,
    reason: "This contains every user's profile on this computer.",
  },
  {
    pattern: /^[A-Za-z]:[\\/]Users[\\/][^\\/]+[\\/]?$/i,
    reason: "This is an entire user profile, containing personal and system files.",
  },
  {
    pattern: /^[A-Za-z]:[\\/]Users[\\/][^\\/]+[\\/](AppData|OneDrive[^\\/]*)[\\/]?$/i,
    reason: "This can contain sensitive application data, credentials, or an entire cloud-synced library.",
  },
  { pattern: /^\/$/, reason: "This is the root of the filesystem, containing every file on the machine." },
  {
    pattern: /^\/(root|etc|usr|System|Applications|private)\/?$/i,
    reason: "This is an operating system directory required for the computer to function.",
  },
  {
    pattern: /^\/(home|Users)\/?$/i,
    reason: "This contains every user's profile on this computer.",
  },
  {
    pattern: /^\/(home|Users)\/[^/]+\/?$/i,
    reason: "This is an entire user profile, containing personal and system files.",
  },
  {
    pattern: /^\/(home|Users)\/[^/]+\/OneDrive[^/]*\/?$/i,
    reason: "This can contain an entire cloud-synced library.",
  },
];

const MEDIUM_PATTERNS: RegExp[] = [
  /^[A-Za-z]:[\\/]Users[\\/][^\\/]+[\\/](Desktop|Downloads|Documents|Pictures)[\\/]?$/i,
  /^\/(home|Users)\/[^/]+\/(Desktop|Downloads|Documents|Pictures)\/?$/i,
];

function matchHigh(candidate: string): string | null {
  const trimmed = candidate.trim();
  if (!trimmed) return "No folder path was provided.";
  for (const { pattern, reason } of HIGH_PATTERNS) {
    if (pattern.test(trimmed)) return reason;
  }
  return null;
}

function matchMedium(candidate: string): boolean {
  const trimmed = candidate.trim();
  return MEDIUM_PATTERNS.some((pattern) => pattern.test(trimmed));
}

export function classifyFolderRisk(rawPath: string, resolvedPath?: string): RiskAssessment {
  const candidates = [rawPath, ...(resolvedPath !== undefined ? [resolvedPath] : [])];

  for (const candidate of candidates) {
    const highReason = matchHigh(candidate);
    if (highReason !== null) {
      return { level: "high", reason: highReason, recommendation: RECOMMENDATION_HIGH };
    }
  }

  for (const candidate of candidates) {
    if (matchMedium(candidate)) {
      return { level: "medium", reason: MEDIUM_REASON, recommendation: RECOMMENDATION_MEDIUM };
    }
  }

  return { level: "low", reason: LOW_REASON, recommendation: RECOMMENDATION_LOW };
}

export function isFolderPathTooBroad(rawPath: string, resolvedPath?: string): boolean {
  return classifyFolderRisk(rawPath, resolvedPath).level === "high";
}
