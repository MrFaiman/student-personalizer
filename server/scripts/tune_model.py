import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import RandomizedSearchCV
from pathlib import Path
import sys
import os


def load_data(grades_path, events_path):
    # Load CSVs
    try:
        df_grades = pd.read_csv(grades_path, encoding='utf-8')
    except UnicodeDecodeError:
        df_grades = pd.read_csv(grades_path, encoding='windows-1255')
        
    try:
        df_events = pd.read_csv(events_path, encoding='utf-8')
    except UnicodeDecodeError:
        df_events = pd.read_csv(events_path, encoding='windows-1255')

    return df_grades, df_events

def extract_features(df_grades, df_events):
    data_rows = []

    for _, grade_row in df_grades.iterrows():
        # ... (previous loading logic same until row construction)
        student_id = grade_row['ת.ז']
        event_rows = df_events[df_events['ת.ז. התלמיד'] == student_id]
        if event_rows.empty:
            continue
        event_row = event_rows.iloc[0]

        meta_cols = ["מס'", "ת.ז", "שם התלמיד", "שכבה", "כיתה", "ממוצע"]
        grade_values = []
        for col in df_grades.columns:
            if col not in meta_cols:
                val = grade_row[col]
                if pd.notna(val):
                    try:
                        grade_values.append(float(val))
                    except ValueError:
                        pass
        
        if not grade_values:
            continue

        avg_grade = np.mean(grade_values)
        min_grade = np.min(grade_values)
        max_grade = np.max(grade_values)
        grade_std = float(np.std(grade_values)) if len(grade_values) > 1 else 0.0
        num_subjects = len(grade_values)
        failing_subjects = sum(1 for g in grade_values if g < 55)

        if len(grade_values) >= 2:
            x = np.arange(len(grade_values), dtype=float)
            grade_trend_slope = float(np.polyfit(x, grade_values, 1)[0])
        else:
            grade_trend_slope = 0.0

        def get_val(row, col_name):
            val = row.get(col_name, 0)
            if pd.isna(val) or val == '':
                return 0
            return float(val)

        absence = get_val(event_row, 'חיסור')
        absence_justified = get_val(event_row, 'חיסור (מוצדק)')
        late = get_val(event_row, 'איחור')
        disturbance = get_val(event_row, 'הפרעה')
        
        no_entry = get_val(event_row, 'אי כניסה לשיעור')
        total_absences = absence + no_entry 
        
        neg_cols = [
            'הפרעה', 'אי כניסה לשיעור', 'תלבושת', 'אי הכנת ש.ב', 
            'אי הבאת ציוד', 'אי ביצוע מטלות בכיתה', 'שימוש בנייד בשטח ביה"ס'
        ]
        total_negative = sum(get_val(event_row, c) for c in neg_cols)

        pos_cols = ['חיזוק חיובי', 'חיזוק חיובי כיתתי']
        total_positive = sum(get_val(event_row, c) for c in pos_cols)
        
        # --- NEW FEATURES ---
        # Ratio of negative events to total events (avoid div by zero)
        total_events = total_negative + total_positive
        negative_positive_ratio = total_negative / total_events if total_events > 0 else 0.0
        
        # Fail ratio
        fail_ratio = failing_subjects / num_subjects if num_subjects > 0 else 0.0

        row = {
            "student_name": grade_row["שם התלמיד"],
            "average_grade": avg_grade,
            "min_grade": min_grade,
            "max_grade": max_grade,
            "grade_std": grade_std,
            "grade_trend_slope": grade_trend_slope,
            "num_subjects": num_subjects,
            "failing_subjects": failing_subjects,
            "absence": absence,
            "absence_justified": absence_justified,
            "late": late,
            "disturbance": disturbance,
            "total_absences": total_absences,
            "total_negative_events": total_negative,
            "total_positive_events": total_positive,
            "negative_positive_ratio": negative_positive_ratio,
            "fail_ratio": fail_ratio
        }
        data_rows.append(row)

    return pd.DataFrame(data_rows)

def tune_models(df):
    feature_columns = [
        "average_grade", "min_grade", "max_grade", "grade_std", "grade_trend_slope",
        "num_subjects", "failing_subjects", "absence", "absence_justified", "late",
        "disturbance", "total_absences", "total_negative_events", "total_positive_events",
        "negative_positive_ratio", "fail_ratio"
    ]

    print(f"Total samples: {len(df)}")
    # ... (rest of setup)
    
    X = df[feature_columns].values
    y_grade = df["average_grade"].values
    
    # Dropout Logic (existing)
    median_negative = df["total_negative_events"].median()
    median_absences = df["total_absences"].median()
    y_dropout = (
        ((df["average_grade"] < 55) & 
         ((df["total_negative_events"] > median_negative) | (df["total_absences"] > median_absences)))
        .astype(int)
        .values
    )

    # --- 1. Tune Grade Predictor (Gradient Boosting) ---
    print("\n--- Tuning Grade Predictor (GradientBoostingRegressor) ---")
    gb_reg = GradientBoostingRegressor(random_state=42)
    
    gb_param_dist = {
        'n_estimators': [100, 200, 300],
        'learning_rate': [0.01, 0.05, 0.1],
        'max_depth': [3, 4, 5],
        'subsample': [0.8, 0.9, 1.0],
        'min_samples_split': [2, 5],
    }
    
    random_search_gb = RandomizedSearchCV(
        gb_reg, 
        param_distributions=gb_param_dist, 
        n_iter=20, 
        cv=5, 
        scoring='neg_mean_absolute_error', 
        n_jobs=-1, 
        random_state=42,
        verbose=1
    )
    random_search_gb.fit(X, y_grade)
    
    print(f"Best GB MAE: {-random_search_gb.best_score_:.4f}")
    print(f"Best GB Params: {random_search_gb.best_params_}")

    # --- 2. Tune Grade Predictor (Random Forest - Baseline Comparison) ---
    print("\n--- Tuning Grade Predictor (Random Forest Baseline) ---")
    rf_reg = RandomForestRegressor(random_state=42)
    rf_param_dist = {
        'n_estimators': [100, 200, 300],
        'max_depth': [None, 10, 20],
        'min_samples_split': [2, 5],
    }
    rf_search = RandomizedSearchCV(rf_reg, rf_param_dist, n_iter=10, cv=5, scoring='neg_mean_absolute_error', n_jobs=-1, random_state=42)
    rf_search.fit(X, y_grade)
    print(f"Best RF MAE: {-rf_search.best_score_:.4f}")

    # --- 3. Tune Dropout Classifier ---
    print("\n--- Tuning Dropout Classifier (RandomForestClassifier) ---")
    
    rf_clf_param_dist = {
        'n_estimators': [50, 100, 200, 300],
        'max_depth': [None, 3, 5, 10, 20],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'max_features': ['sqrt', 'log2', None]
    }

    rf_clf = RandomForestClassifier(random_state=42)
    random_search_clf = RandomizedSearchCV(
        rf_clf, 
        param_distributions=rf_clf_param_dist, 
        n_iter=20, 
        cv=5, 
        scoring='accuracy', 
        n_jobs=-1, 
        random_state=42,
        verbose=1
    )
    random_search_clf.fit(X, y_dropout)
    
    print(f"Best Dropout Accuracy: {random_search_clf.best_score_:.4f}")
    print(f"Best Dropout Params: {random_search_clf.best_params_}")

def compare_models_detailed(df):
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    from sklearn.model_selection import train_test_split
    
    # Best Params found
    gb_params = {'subsample': 0.9, 'n_estimators': 100, 'min_samples_split': 2, 'max_depth': 3, 'learning_rate': 0.05, 'random_state': 42}
    # Using defaults for RF as baseline or the ones we found (MAE 0.94)
    rf_params = {'n_estimators': 100, 'random_state': 42} 

    feature_cols = [
        "average_grade", "min_grade", "max_grade", "grade_std", "grade_trend_slope",
        "num_subjects", "failing_subjects", "absence", "absence_justified", "late",
        "disturbance", "total_absences", "total_negative_events", "total_positive_events",
        "negative_positive_ratio", "fail_ratio"
    ]
    
    X = df[feature_cols].values
    y = df["average_grade"].values
    
    # Split data to see unseen predictions
    X_train, X_test, y_train, y_test, indices_train, indices_test = train_test_split(
        X, y, df.index, test_size=0.2, random_state=42
    )
    
    # Train GB
    gb = GradientBoostingRegressor(**gb_params)
    gb.fit(X_train, y_train)
    
    # Train RF
    rf = RandomForestRegressor(**rf_params)
    rf.fit(X_train, y_train)
    
    # Predict
    gb_preds = gb.predict(X_test)
    rf_preds = rf.predict(X_test)
    
    # Create comparison table
    print(f"{'Student Name':<20} | {'Actual':<7} | {'GB Pred':<7} (Diff) | {'RF Pred':<7} (Diff)")
    print("-" * 75)
    
    test_df = df.loc[indices_test].reset_index()
    
    for i in range(len(y_test)):
        name = test_df.loc[i, 'student_name']
        actual = y_test[i]
        
        gb_p = gb_preds[i]
        gb_diff = abs(gb_p - actual)
        
        rf_p = rf_preds[i]
        rf_diff = abs(rf_p - actual)
        
        # Highlight winner
        gb_mark = "*" if gb_diff < rf_diff else " "
        
        print(f"{name[:19]:<20} | {actual:7.2f} | {gb_p:7.2f} ({gb_diff:4.2f}){gb_mark} | {rf_p:7.2f} ({rf_diff:4.2f})")

    print("-" * 75)
    print(f"* = Closer prediction")

if __name__ == "__main__":
    # Paths (adjust relative to where you run the script, assuming root)
    base_dir = Path(os.getcwd())
    grades_file = base_dir / "data" / "avg_grades.csv"
    events_file = base_dir / "data" / "events.csv"

    if not grades_file.exists():
        print(f"Error: {grades_file} not found.")
        sys.exit(1)
        
    df_grades, df_events = load_data(grades_file, events_file)
    final_df = extract_features(df_grades, df_events)
    
    tune_models(final_df)
    
    print("\n" + "="*50)
    print(" DETAILED COMPARISON: Gradient Boosting vs Random Forest ")
    print("="*50)
    compare_models_detailed(final_df)

def compare_models_detailed(df):
    from sklearn.model_selection import train_test_split
    
    # Best Params found
    gb_params = {'subsample': 0.9, 'n_estimators': 100, 'min_samples_split': 2, 'max_depth': 3, 'learning_rate': 0.05, 'random_state': 42}
    # Using defaults for RF as baseline or the ones we found (MAE 0.94)
    rf_params = {'n_estimators': 100, 'random_state': 42} 

    feature_cols = [
        "average_grade", "min_grade", "max_grade", "grade_std", "grade_trend_slope",
        "num_subjects", "failing_subjects", "absence", "absence_justified", "late",
        "disturbance", "total_absences", "total_negative_events", "total_positive_events",
        "negative_positive_ratio", "fail_ratio"
    ]
    
    X = df[feature_cols].values
    y = df["average_grade"].values
    
    # Split data to see unseen predictions
    X_train, X_test, y_train, y_test, indices_train, indices_test = train_test_split(
        X, y, df.index, test_size=0.2, random_state=42
    )
    
    # Train GB
    gb = GradientBoostingRegressor(**gb_params)
    gb.fit(X_train, y_train)
    
    # Train RF
    rf = RandomForestRegressor(**rf_params)
    rf.fit(X_train, y_train)
    
    # Predict
    gb_preds = gb.predict(X_test)
    rf_preds = rf.predict(X_test)
    
    # Create comparison table
    print(f"{'Student Name':<20} | {'Actual':<7} | {'GB Pred':<7} (Diff) | {'RF Pred':<7} (Diff)")
    print("-" * 75)
    
    test_df = df.loc[indices_test].reset_index()
    
    for i in range(len(y_test)):
        name = test_df.loc[i, 'student_name']
        actual = y_test[i]
        
        gb_p = gb_preds[i]
        gb_diff = abs(gb_p - actual)
        
        rf_p = rf_preds[i]
        rf_diff = abs(rf_p - actual)
        
        # Highlight winner
        gb_mark = "*" if gb_diff < rf_diff else " "
        
        print(f"{name[:19]:<20} | {actual:7.2f} | {gb_p:7.2f} ({gb_diff:4.2f}){gb_mark} | {rf_p:7.2f} ({rf_diff:4.2f})")

    print("-" * 75)
    print(f"* = Closer prediction")
