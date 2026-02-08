import pandas as pd
import numpy as np
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# ==========================================
# 1. Data Loading Functions (ETL)
# ==========================================

def load_grades_file(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parses a wide-format grades file, including the 'Average' column.
    Transposes (melts) the data into: Student | Subject | Teacher | Grade.
    """
    # 1. Define Metadata Columns
    metadata_map = {
        "מס'": "serial_num",
        "ת.ז": "student_tz",
        "שם התלמיד": "student_name",
        "שכבה": "grade_level",
        "כיתה": "class_name"
    }
    
    # Rename matching columns
    df.rename(columns=metadata_map, inplace=True)
    
    # 2. Identify Grade Columns
    metadata_cols = list(metadata_map.values())
    existing_meta_cols = [c for c in metadata_cols if c in df.columns]
    
    # All other columns are treated as grades
    grade_cols = [c for c in df.columns if c not in existing_meta_cols]

    # 3. Melt from Wide to Long
    df_long = df.melt(
        id_vars=existing_meta_cols, 
        value_vars=grade_cols, 
        var_name='subject_teacher_str', 
        value_name='grade'
    )

    # 4. Extract Subject and Teacher from Header
    def parse_header(header_str):
        clean_header = re.sub(r'\.\d+$', '', str(header_str)) # Remove pandas .1, .2
        
        if '-' in clean_header:
            parts = clean_header.split('-', 1)
            return parts[0].strip(), parts[1].strip() # (Subject, Teacher)
        else:
            return clean_header, None # (Subject/Average, None)

    parsed_data = [parse_header(x) for x in df_long['subject_teacher_str']]
    df_long['subject'] = [x[0] for x in parsed_data]
    df_long['teacher_name'] = [x[1] for x in parsed_data]

    # 5. Clean Data
    df_long['grade'] = pd.to_numeric(df_long['grade'], errors='coerce')
    df_long.dropna(subset=['grade'], inplace=True)

    # 6. Add 'period' (Simulated for this test)
    df_long['period'] = 'Q1'
    
    return df_long

def load_attendance_file(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Map Columns
    column_map = {
        "מס'": "serial_num",
        "ת.ז. התלמיד": "student_tz",
        "שם התלמיד": "student_name",
        "שכבה": "grade_level",
        "כיתה": "class_name",
        "שיעורים שדווחו": "lessons_reported",
        "חיסור": "absence",
        "חיסור (מוצדק)": "absence_justified",
        "איחור": "late",
        "איחור (מוצדק)": "late_justified",
        "הפרעה": "disturbance",
        "אי כניסה לשיעור": "skipped_class",
        "אי כניסה לשיעור (מוצדק)": "skipped_class_justified",
        "תלבושת": "uniform_issue",
        "אי הכנת ש.ב": "no_homework",
        "אי הבאת ציוד": "no_equipment",
        "אי ביצוע מטלות בכיתה": "no_classwork",
        "שימוש בנייד בשטח ביה\"ס": "phone_usage",
        "היעדרות בפרטני (מוצדק)": "private_lesson_absence_justified",
        "חיזוק חיובי": "positive_reinforcement",
        "חיזוק חיובי כיתתי": "positive_reinforcement_class",
        "נוכחות בפרטני": "private_lesson_presence"
    }

    df.rename(columns=column_map, inplace=True)

    # 2. Logic Lists
    negative_cols = ['absence', 'absence_justified', 'late', 'disturbance', 
                     'skipped_class', 'skipped_class_justified', 'uniform_issue', 
                     'no_homework', 'no_equipment', 'no_classwork', 'phone_usage']
    
    # 3. Clean Numeric Data
    for col in negative_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        else:
            df[col] = 0

    # 4. Calculations
    df['total_absences'] = df['absence'] + df['absence_justified'] + df.get('skipped_class', 0)
    df['period'] = 'Q1' # Simulated

    return df

# ==========================================
# 2. Analytics Engine
# ==========================================

class DashboardAnalytics:
    def __init__(self, grades_df, attendance_df):
        self.grades = grades_df
        self.attendance = attendance_df

    def get_layer_kpis(self, current_period):
        """Returns Dashboard Homepage KPIs"""
        grades = self.grades[self.grades['period'] == current_period]
        att = self.attendance[self.attendance['period'] == current_period]
        
        # Calculate 'At Risk' (Student Average < 55)
        student_avgs = grades.groupby('student_name')['grade'].mean()
        
        return {
            "layer_average": round(grades['grade'].mean(), 2),
            "avg_absences": round(att['total_absences'].mean(), 1) if not att.empty else 0,
            "at_risk_students": int(student_avgs[student_avgs < 55].count())
        }

    def get_layer_charts(self, current_period):
        """Returns Bar Chart (Class Comparison) data"""
        grades = self.grades[self.grades['period'] == current_period]
        return grades.groupby('class_name')['grade'].mean().reset_index().to_dict(orient='records')

    def get_class_heatmap(self, class_name, current_period):
        """Returns Heatmap Matrix: Student x Subject"""
        df = self.grades[
            (self.grades['class_name'] == class_name) & 
            (self.grades['period'] == current_period)
        ]
        return df.pivot_table(index='student_name', columns='subject', values='grade').fillna(0).reset_index().to_dict(orient='records')

    def get_top_bottom_students(self, class_name, current_period):
        """Returns Top 5 and Bottom 5 lists"""
        df = self.grades[
            (self.grades['class_name'] == class_name) & 
            (self.grades['period'] == current_period)
        ]
        avgs = df.groupby('student_name')['grade'].mean().reset_index()
        return {
            "top_5": avgs.nlargest(5, 'grade').to_dict(orient='records'),
            "bottom_5": avgs.nsmallest(5, 'grade').to_dict(orient='records')
        }

    def get_teacher_stats(self, teacher_name, current_period):
        """Returns Teacher Grade Distribution"""
        df = self.grades[
            (self.grades['teacher_name'] == teacher_name) & 
            (self.grades['period'] == current_period)
        ].copy()
        
        bins = [0, 55, 75, 90, 100]
        labels = ['Fail', 'Medium', 'Good', 'Excellent']
        df['category'] = pd.cut(df['grade'], bins=bins, labels=labels)
        
        return df['category'].value_counts().reset_index().to_dict(orient='records')

    def get_student_radar(self, student_name, current_period):
        """Returns data for Student Radar Chart"""
        df = self.grades[
            (self.grades['student_name'] == student_name) & 
            (self.grades['period'] == current_period)
        ]
        return df[['subject', 'grade']].to_dict(orient='records')

# ==========================================
# 3. Main Test Execution
# ==========================================

if __name__ == "__main__":
    # A. Load your specific files
    # Make sure these filenames match exactly what is in your folder
    try:
        raw_grades = pd.read_excel(DATA_DIR / 'avg_grades.xlsx')
        raw_events = pd.read_excel(DATA_DIR / 'events.xlsx')
        print("Files loaded successfully.")
    except FileNotFoundError as e:
        print(f"Error: {e}. Please check filenames.")
        exit()

    # B. Process Data
    clean_grades = load_grades_file(raw_grades)
    clean_events = load_attendance_file(raw_events)
    
    # C. Initialize Analytics
    analytics = DashboardAnalytics(clean_grades, clean_events)
    PERIOD = 'Q1'

    # --- TEST 1: Layer KPIs ---
    print("\n--- 1. Layer KPIs ---")
    print(analytics.get_layer_kpis(PERIOD))

    # --- TEST 2: Class Heatmap ---
    sample_class = clean_grades['class_name'].unique()[0] # Get first available class
    print(f"\n--- 2. Heatmap for Class {sample_class} (First 2 rows) ---")
    heatmap = analytics.get_class_heatmap(sample_class, PERIOD)
    print(heatmap[:2])

    # --- TEST 3: Top/Bottom Students ---
    print(f"\n--- 3. Top Students in Class {sample_class} ---")
    print(analytics.get_top_bottom_students(sample_class, PERIOD)['top_5'])

    # --- TEST 4: Teacher Stats ---
    # Find a valid teacher name (not None)
    teachers = clean_grades['teacher_name'].dropna().unique()
    if len(teachers) > 0:
        t_name = teachers[0]
        print(f"\n--- 4. Stats for Teacher: {t_name} ---")
        print(analytics.get_teacher_stats(t_name, PERIOD))

    # --- TEST 5: Student Radar ---
    s_name = clean_grades['student_name'].iloc[0]
    print(f"\n--- 5. Radar Data for Student: {s_name} ---")
    print(analytics.get_student_radar(s_name, PERIOD))

    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    import numpy as np
    from math import pi

    # Assumption: Data is already loaded in DataFrames named clean_grades and clean_events
    # (See loading code in previous response)

    # Set clean chart style
    sns.set_theme(style="whitegrid")

    # --- 1. Class Comparison Chart (Layer Level) ---
    plt.figure(figsize=(10, 6))
    layer_data = clean_grades.groupby('class_name')['grade'].mean().reset_index()
    sns.barplot(data=layer_data, x='class_name', y='grade', palette='viridis')
    plt.title('Average Grades by Class (Layer Level)')
    plt.ylim(0, 100)
    plt.ylabel('Average Grade')
    plt.xlabel('Class')
    plt.show()

    # --- 2. Class Heatmap ---
    # Select a sample class
    sample_class = clean_grades['class_name'].unique()[0]
    class_data = clean_grades[clean_grades['class_name'] == sample_class]
    heatmap_matrix = class_data.pivot_table(index='student_name', columns='subject', values='grade').fillna(0)

    plt.figure(figsize=(12, 8))
    sns.heatmap(heatmap_matrix, cmap="YlGnBu", annot=False) # annot=True to display numbers
    plt.title(f'Grade Heatmap - Class {sample_class}')
    plt.ylabel('Student Name')
    plt.xlabel('Subject')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

    # --- 3. Teacher Grade Distribution ---
    # Select a sample teacher
    teacher_name = clean_grades['teacher_name'].dropna().unique()[0]
    teacher_data = clean_grades[clean_grades['teacher_name'] == teacher_name].copy()

    # Categorize grades
    bins = [0, 55, 75, 90, 100]
    labels = ['Fail (<55)', 'Medium (55-75)', 'Good (76-90)', 'Excellent (>90)']
    teacher_data['category'] = pd.cut(teacher_data['grade'], bins=bins, labels=labels)
    dist_data = teacher_data['category'].value_counts().sort_index()

    plt.figure(figsize=(8, 5))
    dist_data.plot(kind='bar', color=['#e74c3c', '#f39c12', '#3498db', '#2ecc71'])
    plt.title(f'Grade Distribution - Teacher: {teacher_name}')
    plt.ylabel('Number of Students')
    plt.xlabel('Grade Category')
    plt.xticks(rotation=0)
    plt.show()

    # --- 4. Student Radar Chart ---
    # Select a sample student
    student_name = clean_grades['student_name'].iloc[0]
    student_data = clean_grades[clean_grades['student_name'] == student_name]
    radar_data = student_data.groupby('subject')['grade'].mean().reset_index()

    # Prepare data for radar chart (requires closing the circle)
    categories = list(radar_data['subject'])
    values = list(radar_data['grade'])
    values += values[:1] # Duplicate first value at the end
    angles = [n / float(len(categories)) * 2 * pi for n in range(len(categories))]
    angles += angles[:1]

    plt.figure(figsize=(8, 8))
    ax = plt.subplot(111, polar=True)
    plt.xticks(angles[:-1], categories, color='grey', size=10)
    ax.plot(angles, values, linewidth=1, linestyle='solid')
    ax.fill(angles, values, 'b', alpha=0.1)
    plt.title(f'Achievement Profile: {student_name}')
    plt.show()