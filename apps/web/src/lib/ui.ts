import type { Category, CaseStatus, Priority } from "./types";

export const priorityMeta: Record<Priority, { label: string; className: string }> = {
  critical: { label: "Critical", className: "badge badge-critical" },
  high: { label: "High", className: "badge badge-high" },
  medium: { label: "Medium", className: "badge badge-medium" },
  low: { label: "Low", className: "badge badge-low" },
};

export const statusMeta: Record<CaseStatus, { label: string; className: string }> = {
  new: { label: "New", className: "status status-new" },
  analyzed: { label: "Needs review", className: "status status-analyzed" },
  approved: { label: "Approved", className: "status status-approved" },
  overridden: { label: "Overridden", className: "status status-overridden" },
  rejected: { label: "Rejected", className: "status status-rejected" },
};

export const categoryLabels: Record<Category, string> = {
  incident: "Incident",
  access: "Access",
  procurement: "Procurement",
  compliance: "Compliance",
  service: "Service",
  other: "Other",
};

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function titleCase(value: string): string {
  return value
    .split(/[._-]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
