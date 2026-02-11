import clsx, { type ClassValue } from "clsx";
import { format as dateFnsFormat, parseISO } from "date-fns";

/**
 * Merge class names conditionally.
 * Uses clsx for conditional class joining.
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

/**
 * Format a number with locale-aware thousand separators.
 * e.g. 1234 -> "1,234"
 */
export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

/**
 * Format a date string or Date object using date-fns format tokens.
 * @param date - ISO string or Date object
 * @param formatStr - date-fns format string (default: "yyyy/MM/dd")
 */
export function formatDate(
  date: string | Date,
  formatStr: string = "yyyy/MM/dd"
): string {
  const d = typeof date === "string" ? parseISO(date) : date;
  return dateFnsFormat(d, formatStr);
}
