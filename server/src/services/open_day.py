import re
import uuid
from io import BytesIO

import pandas as pd
from sqlmodel import Session

from ..models import OpenDayImport, OpenDayRegistration
from ..schemas.open_day import OpenDayUploadResponse

# Maps English field names to substrings to look for in Hebrew column headers
_COLUMN_KEYWORDS: dict[str, list[str]] = {
    "submitted_at": ["חותמת זמן", "timestamp"],
    "first_name": ["שם פרטי"],
    "last_name": ["שם משפחה"],
    "student_id": ["ת.ז"],
    "parent_name": ["שם ההורה"],
    "phone": ["טלפון"],
    "email": ["דואר אלקטרוני"],
    "current_school": ["בית הספר הנוכחי"],
    "next_grade": ["עולה", "לכיתה"],
    "interested_track": ["מתעניין", "מגמה"],
    "referral_source": ["שמעתם"],
    "additional_notes": ["להוסיף"],
}


class OpenDayService:
    def __init__(self, session: Session):
        self.session = session

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename Hebrew column headers to English field names."""
        rename_map: dict[str, str] = {}
        for field_name, keywords in _COLUMN_KEYWORDS.items():
            for col in df.columns:
                if any(kw in col for kw in keywords) and col not in rename_map:
                    rename_map[col] = field_name
                    break
        return df.rename(columns=rename_map)

    def _normalize_phone(self, val) -> str | None:
        """Clean, complete, and validate an Israeli mobile phone number.

        Strips non-digit characters, prepends a leading zero if missing
        (e.g. 508499043 -> 0508499043), then validates the Israeli mobile
        format 05X-XXXXXXX (10 digits starting with 05[0-9]).
        Returns the normalised digits-only string, or None if invalid/empty.
        """
        raw = self._clean(val)
        if raw is None:
            return None
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return None
        # Prepend leading zero for 9-digit numbers starting with 5
        if len(digits) == 9 and digits.startswith("5"):
            digits = "0" + digits
        if not re.fullmatch(r"05\d{8}", digits):
            return None
        return digits

    def _clean(self, val) -> str | None:
        """Convert a cell value to a stripped string, returning None for empty/NaN."""
        if val is None:
            return None
        try:
            if pd.isna(val):
                return None
        except (TypeError, ValueError):
            pass
        s = str(val).strip()
        return None if s.lower() in ("nan", "none", "") else s

    def process_upload(self, mime_format: str, content: bytes, filename: str, *, school_id: int | None) -> OpenDayUploadResponse:
        """Process an uploaded Excel or CSV file containing open day registrations."""
        if mime_format == "csv":
            df = pd.read_csv(BytesIO(content), encoding="utf-8")
        else:
            df = pd.read_excel(BytesIO(content), engine="openpyxl")

        df = self._normalize_columns(df)

        batch_id = str(uuid.uuid4())
        rows_imported = 0
        rows_failed = 0
        errors: list[str] = []

        import_log = OpenDayImport(batch_id=batch_id, filename=filename, school_id=school_id)
        self.session.add(import_log)
        self.session.flush()

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # type: ignore[arg-type]
            try:
                first_name = self._clean(row.get("first_name")) or ""
                last_name = self._clean(row.get("last_name")) or ""
                if not first_name and not last_name:
                    errors.append(f"שורה {row_num}: חסר שם תלמיד/ה")
                    rows_failed += 1
                    continue

                # student_id may arrive as float (e.g. 338962004.0)
                raw_id = row.get("student_id")
                student_id: str | None = None
                if raw_id is not None:
                    try:
                        if pd.notna(raw_id):
                            student_id = str(int(float(str(raw_id).replace(",", ""))))
                    except (ValueError, TypeError):
                        student_id = self._clean(raw_id)

                # submitted_at may be a datetime object or a string
                submitted_at = None
                raw_ts = row.get("submitted_at")
                if raw_ts is not None:
                    try:
                        if pd.notna(raw_ts):
                            submitted_at = pd.to_datetime(raw_ts).to_pydatetime()
                    except (ValueError, TypeError):
                        pass

                self.session.add(
                    OpenDayRegistration(
                        import_id=import_log.id,
                        school_id=school_id,
                        submitted_at=submitted_at,
                        first_name=first_name,
                        last_name=last_name,
                        student_id=student_id,
                        parent_name=self._clean(row.get("parent_name")),
                        phone=self._normalize_phone(row.get("phone")),
                        email=self._clean(row.get("email")),
                        current_school=self._clean(row.get("current_school")),
                        next_grade=self._clean(row.get("next_grade")),
                        interested_track=self._clean(row.get("interested_track")),
                        referral_source=self._clean(row.get("referral_source")),
                        additional_notes=self._clean(row.get("additional_notes")),
                    )
                )
                rows_imported += 1
            except Exception as exc:
                errors.append(f"שורה {row_num}: {exc}")
                rows_failed += 1

        import_log.rows_imported = rows_imported
        import_log.rows_failed = rows_failed
        self.session.commit()

        return OpenDayUploadResponse(
            batch_id=batch_id,
            rows_imported=rows_imported,
            rows_failed=rows_failed,
            errors=errors[:20],
        )
