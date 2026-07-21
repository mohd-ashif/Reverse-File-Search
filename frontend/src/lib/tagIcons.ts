import {
  BadgeDollarSign,
  FileSignature,
  FileText,
  Landmark,
  Mail,
  Receipt,
  ShoppingCart,
  Stethoscope,
  Tag,
  UserRound,
  type LucideIcon,
} from "lucide-react";

// Icon per well-known document category. Anything outside this list (a
// custom category the model came up with) falls back to a generic tag icon.
const KNOWN_TAG_ICONS: Record<string, LucideIcon> = {
  invoice: FileText,
  contract: FileSignature,
  resume: UserRound,
  tax: Landmark,
  "purchase order": ShoppingCart,
  "medical record": Stethoscope,
  "salary slip": BadgeDollarSign,
  "bank statement": Landmark,
  receipt: Receipt,
  letter: Mail,
};

export function tagIcon(tag: string): LucideIcon {
  return KNOWN_TAG_ICONS[tag.trim().toLowerCase()] ?? Tag;
}
