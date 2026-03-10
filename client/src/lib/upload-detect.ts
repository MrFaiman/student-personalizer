import type { ImportResponse } from "@/lib/types";

export type FileTypeValue = "grades" | "events";
export type UploadStatus = "pending" | "uploading" | "success" | "failed";
export type ValidationStatus = "ready" | "needs-input" | "duplicate";

export interface StagedFile {
    id: string;
    file: File;
    filename: string;
    detectedFileType?: FileTypeValue;
    detectedPeriod?: string;
    detectedYear?: string;
    overrideFileType?: FileTypeValue | "__auto__";
    overridePeriod?: string;
    overrideYear?: string;
    validationStatus: ValidationStatus;
    uploadStatus: UploadStatus;
    result?: ImportResponse;
    error?: string;
}

export function detectFromFilename(filename: string): { fileType?: FileTypeValue; period?: string; year?: string } {
    const name = filename.toLowerCase().replace(/\.(xlsx|xls|csv)$/i, "");

    // Period: _Q1_, _Q2_, _Q3_, _Q4_
    const periodMatch = name.match(/_(q[1-4])(?:_|$)/i);
    const period = periodMatch ? periodMatch[1].toUpperCase() : undefined;

    // Year: 2024-2025 or 2024 (single year normalized to range)
    const yearMatch = name.match(/(\d{4}-\d{4}|\d{4})(?:_|$)/);
    let year: string | undefined;
    if (yearMatch) {
        const raw = yearMatch[1];
        if (raw.includes("-")) {
            year = raw;
        } else {
            const y = parseInt(raw, 10);
            year = `${y}-${y + 1}`;
        }
    }

    // File type: avg_grades_* → grades, events_* → events
    let fileType: FileTypeValue | undefined;
    if (name.includes("avg_grades") || /(?:^|_)grades(?:_|$)/.test(name)) {
        fileType = "grades";
    } else if (/(?:^|_)events(?:_|$)/.test(name)) {
        fileType = "events";
    }

    return { fileType, period, year };
}

export function resolvedFileType(sf: Pick<StagedFile, "overrideFileType" | "detectedFileType">): FileTypeValue | undefined {
    const v = sf.overrideFileType;
    return v && v !== "__auto__" ? v : sf.detectedFileType;
}

export function resolvedPeriod(sf: Pick<StagedFile, "overridePeriod" | "detectedPeriod">): string | undefined {
    return sf.overridePeriod || sf.detectedPeriod;
}

export function resolvedYear(sf: Pick<StagedFile, "overrideYear" | "detectedYear">): string | undefined {
    return sf.overrideYear || sf.detectedYear;
}

export function validateStagedFile(sf: StagedFile, all: StagedFile[]): ValidationStatus {
    if (all.some(o => o.id !== sf.id && o.filename === sf.filename)) return "duplicate";
    if (!resolvedFileType(sf) || !resolvedPeriod(sf) || !resolvedYear(sf)) return "needs-input";
    return "ready";
}

export function createStagedFile(file: File, existing: StagedFile[]): StagedFile {
    const d = detectFromFilename(file.name);
    const sf: StagedFile = {
        id: crypto.randomUUID(),
        file,
        filename: file.name,
        detectedFileType: d.fileType,
        detectedPeriod: d.period,
        detectedYear: d.year,
        validationStatus: "ready",
        uploadStatus: "pending",
    };
    sf.validationStatus = validateStagedFile(sf, existing);
    return sf;
}

export function revalidateAll(files: StagedFile[]): StagedFile[] {
    return files.map(sf =>
        sf.uploadStatus !== "pending" ? sf : { ...sf, validationStatus: validateStagedFile(sf, files) }
    );
}
