/**
 * Utility functions for handling Hebrew years.
 * Converts a Gregorian academic year (e.g., "2024" or "2024-2025") 
 * to its Hebrew year acronym equivalent (e.g., "תשפ״ה").
 */

const hebrewYearMap: Record<number, string> = {
    2010: "תשע״א",
    2011: "תשע״ב",
    2012: "תשע״ג",
    2013: "תשע״ד",
    2014: "תשע״ה",
    2015: "תשע״ו",
    2016: "תשע״ז",
    2017: "תשע״ח",
    2018: "תשע״ט",
    2019: "תש״פ",
    2020: "תשפ״א",
    2021: "תשפ״ב",
    2022: "תשפ״ג",
    2023: "תשפ״ד",
    2024: "תשפ״ה",
    2025: "תשפ״ו",
    2026: "תשפ״ז",
    2027: "תשפ״ח",
    2028: "תשפ״ט",
    2029: "תש״צ",
    2030: "תשצ״א",
};

/**
 * Formats a Gregorian academic year start into a Hebrew year string.
 * @param year The start year as number (2024) or string ("2024", "2024-2025")
 * @returns The formatted Hebrew year, or the original string if parsing fails or year is out of range.
 */
export function formatHebrewYear(year: string | number | undefined | null): string {
    if (!year) return "";

    // Extract the starting year if it's a range (e.g. "2024-2025" -> 2024)
    const yearStr = String(year).trim();
    const startYearMatch = yearStr.match(/^(\d{4})/);

    if (startYearMatch) {
        const startYearNum = parseInt(startYearMatch[1], 10);
        const hebrewStr = hebrewYearMap[startYearNum];
        if (hebrewStr) {
            // Check if original string actually contains a range like "-2025" and preserve it
            // or if it's just "2024", format it as "2024-2025"
            const rangeStr = yearStr.includes("-") ? yearStr : `${startYearNum}-${startYearNum + 1}`;
            return `${hebrewStr} (${rangeStr})`;
        }
    }

    // Fallback to the original string if we can't map it
    return yearStr;
}
