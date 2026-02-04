# Pedagogical Dashboard (דשבורד פדגוגי) 🎓

מערכת BI אינטראקטיבית לניתוח הישגים לימודיים, התנהגות ונוכחות בבית הספר. [cite_start]המערכת מאפשרת לצוות הפדגוגי לקבל תמונת מצב שכבתית, כיתתית ופרטנית על בסיס נתונים שוטפים[cite: 3].

## 🛠 Tech Stack

* **Language:** Python 3.12+
* **Package Manager:** [uv](https://github.com/astral-sh/uv) (Blazing fast Python package installer and resolver)
* **Backend Framework:** FastAPI
* **Database:** PostgreSQL
* **Data Processing:** Pandas (Excel manipulation)
* **ORM:** SQLAlchemy / SQLModel (Recommended)

---

## 📋 Project Specifications & Features

המערכת נבנתה על בסיס מסמך אפיון דרישות מפורט וכוללת את היכולות הבאות:

### 1. Data Ingestion (טעינת נתונים)
* [cite_start]**Excel Import:** תמיכה בייבוא קבצי אקסל גולמיים במנגנון Drag & Drop[cite: 17].
* **Data Types:**
    * [cite_start]**דוח ציונים:** שם תלמיד, כיתה, מקצוע, מורה, ציון, תאריך/תקופה [cite: 6-12].
    * [cite_start]**דוח נוכחות/התנהגות:** סכימת אירועים (חיסור, איחור, הפרעה, תלבושת וכו') [cite: 13-14].
* [cite_start]**Validation:** בדיקת תקינות קובץ לפני שמירה ב-DB[cite: 18].
* [cite_start]**Period Tagging:** שיוך הקובץ לתקופה ספציפית (רבעון/מחצית) לצורך השוואות[cite: 19].

### 2. Analytics & Visualizations
המערכת מספקת ויזואליזציה ברמות חיתוך שונות:

* **מבט על (Dashboard Homepage):**
    * [cite_start]KPIs: ממוצע שכבה, אחוז היעדרות, מונה תלמידים בסיכון (ממוצע < 55)[cite: 29].
    * [cite_start]השוואת ממוצעים בין כיתות (Bar Chart) ומגמת היעדרות שנתית (Line Chart) [cite: 30-31].
* **מבט כיתתי (Class Level):**
    * [cite_start]Heatmap: זיהוי תלמידים מאתגרים רוחבית (ציר X מקצועות / ציר Y תלמידים)[cite: 36].
    * [cite_start]טבלאות "מצטיינים" ו"מאתגרים"[cite: 37].
* **מבט פרטני (Student Profile):**
    * [cite_start]גרף רדאר (Radar Chart) להצגת הישגים בכל המקצועות[cite: 43].
    * [cite_start]מד חיסורים ביחס לממוצע הכיתתי[cite: 44].
    * [cite_start]חיווי מגמה (שיפור/ירידה) ביחס לתקופה קודמת[cite: 45].

### 3. Filtering & Search
[cite_start]סרגל צד דינמי המאפשר סינון לפי: טווח זמנים, כיתה, מקצוע, שם מורה ושם תלמיד [cite: 20-26].

---

## 🗄️ Database Schema Concepts

המערכת משתמשת ב-PostgreSQL. על בסיס האפיון, יש ליצור קשרי גומלין (Relations) לפי הלוגיקה הבאה:

* [cite_start]**Primary Keys:** זיהוי ייחודי או שילוב של "שם תלמיד" + "כיתה"[cite: 52].
* [cite_start]**Date Handling:** תמיכה בפורמט `DD/MM/YYYY`[cite: 53].
* [cite_start]**Logic:** סכימה (Sum) של עמודת "כמות שעות" מדוחות הנוכחות לחישוב סך חיסורים[cite: 54].

---

## 🚀 Getting Started

פרויקט זה משתמש ב-`uv` לניהול תלויות וסביבות וירטואליות.

### Prerequisites
* Python installed
* PostgreSQL running (Locally or via Docker)
* `uv` installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/MrFaiman/student-personalizer.git](https://github.com/MrFaiman/student-personalizer.git)
    cd pedagogical-dashboard
    ```

2.  **Initialize Virtual Environment & Install Dependencies:**
    ```bash
    uv venv
    # On Windows: .venv\Scripts\activate
    # On Mac/Linux: source .venv/bin/activate
    
    uv pip install fastapi uvicorn sqlalchemy psycopg2-binary pandas openpyxl python-multipart
    ```
    *(Note: Adjust dependencies based on your specific `pyproject.toml` or requirements).*

3.  **Environment Variables (.env):**
    Create a `.env` file in the root directory:
    ```env
    DATABASE_URL=postgresql://user:password@localhost:5432/dashboard_db
    SECRET_KEY=your_secret_key
    ```

4.  **Run the Server:**
    ```bash
    uv run fastapi dev main.py
    ```
    The API will be available at `http://127.0.0.1:5173`.
    Access the auto-generated docs at `http://127.0.0.1:5173/docs`.

---