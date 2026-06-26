"""
Personalized Learning Path Generator - Interest Checking Module
----------------------------------------------------------------
Description:
    This module collects student input, analyzes their interests, 
    and predicts the most suitable learning domain using machine learning.
    It uses a dataset for training and provides personalized recommendations.

Requirements:
    pip install pandas scikit-learn matplotlib joblib numpy flask flask-cors
"""

import os
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report




# ===============================================================
# Configuration
# ===============================================================
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "interest_model.joblib")
DATASET_PATH = os.path.join(os.path.dirname(__file__), "data", "student_interests.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "student_results")
LABEL_CANDIDATES = ["predicted_domain", "label", "target", "interest_domain"]
KAGGLE_DATASET_REFERENCE = os.getenv("INTEREST_KAGGLE_DATASET_REFERENCE", "")
ENABLE_GENERIC_DATASET_ADAPTATION = os.getenv("INTEREST_ENABLE_GENERIC_DATASET_ADAPTATION", "true").lower() == "true"

# Allow overriding dataset via env for flexibility
DATASET_OVERRIDE = os.getenv("INTEREST_DATASET_PATH")
AUTO_RETRAIN_ON_DATASET_CHANGE = os.getenv(
    "INTEREST_AUTO_RETRAIN_ON_DATASET_CHANGE",
    "true",
).lower() == "true"

# Learning Domains
DOMAINS = [
    "Coding",
    "Web Development", 
    "Game Development", 
    "Cybersecurity",
    "Data Science",
    "Mobile Development",
    "Cloud Computing",
    "AI & Machine Learning",
    "Physical Games / Sports"
]

DOMAIN_KEYWORDS = {
    "Coding": ["coding", "programming", "software", "developer", "python", "java", "c++", "algorithm"],
    "Web Development": ["web", "frontend", "backend", "full stack", "html", "css", "javascript", "react", "node"],
    "Game Development": ["game", "unity", "unreal", "gameplay", "3d", "graphics"],
    "Cybersecurity": ["security", "cyber", "hacking", "pentest", "forensics", "network security", "owasp"],
    "Data Science": ["data", "analytics", "analysis", "statistics", "sql", "visualization", "bi"],
    "Mobile Development": ["mobile", "android", "ios", "swift", "kotlin", "flutter", "react native"],
    "Cloud Computing": ["cloud", "aws", "azure", "gcp", "devops", "kubernetes", "docker"],
    "AI & Machine Learning": ["ai", "ml", "machine learning", "deep learning", "nlp", "computer vision", "llm"],
    "Physical Games / Sports": ["sports", "athlete", "fitness", "physical", "training", "coach"],
}


def get_official_learning_curricula(domain: str) -> dict:
    """
    Dynamic curriculum from the OpenAI learning-path API (no static domain_roadmap_data).
    """
    try:
        from advanced_learning_path.engine import AdvancedLearningPathEngine

        engine = AdvancedLearningPathEngine()
        result = engine.generate_roadmap(domain, {"user": {}})
        roadmap = result.get("roadmap") or {}

        def _stage_block(*keys: str) -> dict:
            for key in keys:
                block = roadmap.get(key)
                if isinstance(block, dict) and (block.get("topics") or block.get("all_topics")):
                    return block
            return {}

        def _topics(*keys: str) -> list:
            block = _stage_block(*keys)
            full = block.get("all_topics") or block.get("topics") or []
            return [str(t) for t in full if str(t).strip()]

        def _projects(*keys: str) -> list:
            block = _stage_block(*keys)
            projects = block.get("stage_projects") or []
            return [str(p) for p in projects if str(p).strip()]

        return {
            "topic_roadmap": {
                "Beginner": _topics("basic", "beginner"),
                "Intermediate": _topics("intermediate"),
                "Advanced": _topics("advanced", "expert"),
            },
            "stage_project_roadmap": {
                "Beginner": _projects("basic", "beginner"),
                "Intermediate": _projects("intermediate"),
                "Advanced": _projects("advanced", "expert"),
            },
        }
    except Exception:
        return {
            "topic_roadmap": {"Beginner": [], "Intermediate": [], "Advanced": []},
            "stage_project_roadmap": {"Beginner": [], "Intermediate": [], "Advanced": []},
        }


KAGGLE_DEVILDYNO_COLUMN_HINTS = [
    "What are your skills ? (Select multiple if necessary)",
    "What are your interests?",
    "If yes, then what is/was your first Job title in your current field of work? If not applicable, write NA.",
    "What was your course in UG?",
]

KAGGLE_ROLE_TO_DOMAIN = {
    "software developer": "Coding",
    "software engineer": "Coding",
    "software tester": "Coding",
    "technical support": "Coding",
    "technical writer": "Coding",
    "web developer": "Web Development",
    "ui/ux designer": "Web Development",
    "ui ux designer": "Web Development",
    "frontend developer": "Web Development",
    "backend developer": "Web Development",
    "full stack developer": "Web Development",
    "game developer": "Game Development",
    "cyber security analyst": "Cybersecurity",
    "security analyst": "Cybersecurity",
    "ethical hacker": "Cybersecurity",
    "data analyst": "Data Science",
    "data scientist": "Data Science",
    "business analyst": "Data Science",
    "mobile app developer": "Mobile Development",
    "android developer": "Mobile Development",
    "ios developer": "Mobile Development",
    "cloud engineer": "Cloud Computing",
    "devops engineer": "Cloud Computing",
    "ml engineer": "AI & Machine Learning",
    "machine learning engineer": "AI & Machine Learning",
    "ai engineer": "AI & Machine Learning",
    "sports analyst": "Physical Games / Sports",
    "fitness coach": "Physical Games / Sports",
}

NUMERIC_COLUMN_HINTS = {
    "Coding": ["coding", "programming", "logic", "math", "problem"],
    "Web Development": ["web", "frontend", "backend", "ui", "ux"],
    "Game Development": ["game", "graphics", "design", "creative"],
    "Cybersecurity": ["security", "network", "privacy", "risk"],
    "Data Science": ["data", "stats", "analysis", "math", "research"],
    "Mobile Development": ["mobile", "android", "ios", "app"],
    "Cloud Computing": ["cloud", "devops", "infrastructure", "system"],
    "AI & Machine Learning": ["ai", "ml", "machine", "algorithm", "model"],
    "Physical Games / Sports": ["sports", "fitness", "physical", "health"],
}

# Ensure directories exist
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cache the loaded model in-memory for API performance
_MODEL_CACHE = None


def _resolve_dataset_path(dataset_path: str | None = None) -> str:
    return dataset_path or DATASET_OVERRIDE or DATASET_PATH


def _dataset_newer_than_model(dataset_path: str | None) -> bool:
    """
    Return True when dataset exists and is newer than the model artifact.
    This keeps training dynamic when CSV is replaced/updated.
    """
    try:
        target_dataset = _resolve_dataset_path(dataset_path)
        if not target_dataset or not os.path.exists(target_dataset):
            return False
        if not os.path.exists(MODEL_PATH):
            return True
        return os.path.getmtime(target_dataset) > os.path.getmtime(MODEL_PATH)
    except Exception:
        return False


# ===============================================================
# Function: Generate Synthetic Dataset
# ===============================================================
def generate_synthetic_dataset(domains: list, samples: int = 1000) -> pd.DataFrame:
    """
    Generates a synthetic dataset to simulate student interest patterns.

    Args:
        domains (list): List of learning domains.
        samples (int): Number of synthetic samples.

    Returns:
        pd.DataFrame: Synthetic dataset with features and labels.
    """
    # Deprecated in dynamic mode; retained only for backward compatibility.
    np.random.seed(42)
    data, labels = [], []

    for i in range(samples):
        # Generate random base scores
        row = np.random.randint(1, 11, size=len(domains))
        
        # Pick a dominant interest and boost it
        dominant = np.random.choice(len(domains))
        row[dominant] = min(10, row[dominant] + np.random.randint(2, 6))
        
        # Sometimes add secondary interest
        if np.random.random() > 0.5:
            secondary = np.random.choice([i for i in range(len(domains)) if i != dominant])
            row[secondary] = min(10, row[secondary] + np.random.randint(1, 3))
        
        data.append(row)
        labels.append(domains[dominant])

    df = pd.DataFrame(data, columns=domains)
    df["predicted_domain"] = labels
    df["student_id"] = [f"STUDENT_{i+1:04d}" for i in range(samples)]
    
    return df


# ===============================================================
# Function: Detect Label Column
# ===============================================================
def detect_label_column(df: pd.DataFrame) -> str | None:
    """Return the first matching label column name or None."""
    for cand in LABEL_CANDIDATES:
        if cand in df.columns:
            return cand
    return None


# ===============================================================
# Function: Generic dataset adaptation (Kaggle -> PLPG domains)
# ===============================================================
def _normalize_series_to_0_10(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if values.notna().sum() == 0:
        return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)
    vmin = float(values.min())
    vmax = float(values.max())
    if np.isclose(vmin, vmax):
        return pd.Series(np.full(len(series), 5.0), index=series.index, dtype=float)
    normalized = (values - vmin) / (vmax - vmin)
    normalized = normalized.fillna(normalized.mean() if not np.isnan(normalized.mean()) else 0.5)
    return (normalized * 10.0).clip(0.0, 10.0)


def _score_row_from_text(text: str) -> dict[str, float]:
    text = (text or "").strip().lower()
    scores = {domain: 0.0 for domain in DOMAINS}
    if not text:
        return scores
    for domain, keywords in DOMAIN_KEYWORDS.items():
        matches = 0
        for keyword in keywords:
            pattern = rf"\b{re.escape(keyword.lower())}\b"
            matches += len(re.findall(pattern, text))
        scores[domain] = min(10.0, 1.0 + (matches * 1.8)) if matches > 0 else 0.0
    return scores


def _normalize_token_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _detect_devildyno_dataset(df: pd.DataFrame) -> bool:
    columns = set(str(c).strip() for c in df.columns)
    hits = sum(1 for hint in KAGGLE_DEVILDYNO_COLUMN_HINTS if hint in columns)
    return hits >= 2


def _map_role_to_domain(role_value: object) -> str | None:
    role = _normalize_token_text(role_value)
    if not role or role in {"na", "n/a", "none", "null"}:
        return None
    if role in KAGGLE_ROLE_TO_DOMAIN:
        return KAGGLE_ROLE_TO_DOMAIN[role]
    for key, domain in KAGGLE_ROLE_TO_DOMAIN.items():
        if key in role:
            return domain
    return None


def adapt_devildyno_career_dataset_to_plpg(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deterministic adapter for:
    https://www.kaggle.com/datasets/devildyno/computer-science-students-career-prediction
    """
    if df.empty:
        raise ValueError("Devildyno dataset is empty")

    skill_col = "What are your skills ? (Select multiple if necessary)"
    interest_col = "What are your interests?"
    role_col = "ROLE"
    first_job_col = "If yes, then what is/was your first Job title in your current field of work? If not applicable, write NA."
    ug_course_col = "What was your course in UG?"
    ug_specialization_col = "What is your UG specialization? Major Subject (Eg; Mathematics)"
    cert_col = "If yes, please specify your certificate course title."
    masters_col = "Have you done masters after undergraduation? If yes, mention your field of masters.(Eg; Masters in Mathematics)"

    rows = []
    for _, row in df.iterrows():
        text_parts = []
        for col in [skill_col, interest_col, first_job_col, ug_course_col, ug_specialization_col, cert_col, masters_col]:
            if col in df.columns and pd.notna(row.get(col)):
                text_parts.append(str(row.get(col)))
        combined_text = " ; ".join(text_parts)
        domain_scores = _score_row_from_text(combined_text)

        # Convert sparse NLP scores to full 0-10 range.
        dense_scores = {}
        for domain in DOMAINS:
            dense_scores[domain] = int(round(max(0.0, min(10.0, domain_scores.get(domain, 0.0)))))

        role_label = _map_role_to_domain(row.get(role_col)) if role_col in df.columns else None
        first_job_label = _map_role_to_domain(row.get(first_job_col)) if first_job_col in df.columns else None
        label = role_label or first_job_label

        if not any(v > 0 for v in dense_scores.values()):
            dense_scores["Coding"] = 5
            dense_scores["Web Development"] = 4
            dense_scores["Data Science"] = 4

        if label is None:
            label = max(dense_scores.items(), key=lambda item: item[1])[0]

        rows.append({**dense_scores, "predicted_domain": label})

    out = pd.DataFrame(rows)
    out = out[out["predicted_domain"].isin(DOMAINS)].reset_index(drop=True)
    if out.empty:
        raise ValueError("Devildyno adaptation produced no valid labeled rows")
    return out[DOMAINS + ["predicted_domain"]]


def adapt_generic_dataset_to_plpg(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adapt a generic educational/career CSV (e.g., Kaggle) into PLPG schema.
    Produces 0-10 domain columns + predicted_domain label.
    """
    if df.empty:
        raise ValueError("Input dataset is empty")

    if _detect_devildyno_dataset(df):
        return adapt_devildyno_career_dataset_to_plpg(df)

    text_cols = [c for c in df.columns if pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c])]
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    normalized_numeric = {col: _normalize_series_to_0_10(df[col]) for col in numeric_cols}

    domain_numeric_scores = {domain: np.zeros(len(df), dtype=float) for domain in DOMAINS}
    for domain in DOMAINS:
        hints = NUMERIC_COLUMN_HINTS[domain]
        matched_cols = [
            col for col in numeric_cols
            if any(hint in str(col).lower() for hint in hints)
        ]
        if not matched_cols:
            continue
        matrix = np.column_stack([normalized_numeric[col].to_numpy() for col in matched_cols])
        domain_numeric_scores[domain] = np.nanmean(matrix, axis=1)

    rows = []
    for idx, row in df.iterrows():
        text_blob = " ".join(str(row[col]) for col in text_cols if pd.notna(row[col]))
        text_scores = _score_row_from_text(text_blob)
        combined = {}
        for domain in DOMAINS:
            numeric_signal = float(domain_numeric_scores[domain][idx]) if len(domain_numeric_scores[domain]) > idx else 0.0
            score = (0.65 * float(text_scores[domain])) + (0.35 * numeric_signal)
            combined[domain] = int(round(max(0.0, min(10.0, score))))

        if not any(v > 0 for v in combined.values()):
            fallback = idx % len(DOMAINS)
            combined[DOMAINS[fallback]] = 6

        predicted_domain = max(combined.items(), key=lambda item: item[1])[0]
        rows.append({**combined, "predicted_domain": predicted_domain})

    out = pd.DataFrame(rows)
    for domain in DOMAINS:
        if domain not in out.columns:
            out[domain] = 0
    out = out[DOMAINS + ["predicted_domain"]]
    return out


# ===============================================================
# Function: Load Dataset from CSV (manual loader)
# ===============================================================
def load_dataset_from_csv(csv_path: str, domains: list) -> pd.DataFrame:
    """
    Loads a CSV dataset and validates required columns.

    Args:
        csv_path (str): Path to CSV file.
        domains (list): Expected domain columns.

    Returns:
        pd.DataFrame: Loaded dataset with required columns.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8")
    missing = [d for d in domains if d not in df.columns]
    if missing:
        if not ENABLE_GENERIC_DATASET_ADAPTATION:
            raise ValueError(f"Dataset is missing required domain columns: {missing}")
        adapted_df = adapt_generic_dataset_to_plpg(df)
        adapted_df.to_csv(csv_path, index=False)
        ref_text = f" Reference source: {KAGGLE_DATASET_REFERENCE}" if KAGGLE_DATASET_REFERENCE else ""
        print(
            "Dataset did not match PLPG schema; auto-adapted generic dataset to domain columns."
            f"{ref_text}"
        )
        df = adapted_df

    label_col = detect_label_column(df)
    if label_col is None:
        # Create pseudo-label from max domain score if none provided
        df["predicted_domain"] = df[domains].idxmax(axis=1)
    else:
        # Normalize to our canonical name
        if label_col != "predicted_domain":
            df = df.rename(columns={label_col: "predicted_domain"})

    return df


# ===============================================================
# Function: Load or Create Dataset
# ===============================================================
def load_or_create_dataset(dataset_path: str | None = None) -> pd.DataFrame:
    """
    Loads the dataset from CSV or creates a synthetic one if not found.

    Args:
        dataset_path (str | None): Explicit dataset path. If None, uses env override or default.

    Returns:
        pd.DataFrame: The training dataset.
    """
    target_path = dataset_path or DATASET_OVERRIDE or DATASET_PATH

    print(f"Loading dataset from: {target_path}")
    if not target_path:
        raise ValueError(
            "No dataset path configured. Set INTEREST_DATASET_PATH to a Kaggle CSV file path."
        )

    df = load_dataset_from_csv(target_path, DOMAINS)
    if df.empty:
        raise ValueError(f"Dataset is empty: {target_path}")

    print(f"Loaded {len(df)} records.")
    return df


# ===============================================================
# Function: Train Model
# ===============================================================
def train_model(df: pd.DataFrame = None, force_retrain: bool = False, dataset_path: str | None = None):
    """
    Trains the interest prediction model.

    Args:
        df (pd.DataFrame): Training dataset.
        force_retrain (bool): If True, retrains even if model exists.
        dataset_path (str | None): Optional dataset path override.

    Returns:
        RandomForestClassifier: Trained model.
    """
    global _MODEL_CACHE

    # Use cached model if present
    if _MODEL_CACHE is not None and not force_retrain:
        return _MODEL_CACHE

    # Check if model already exists
    if os.path.exists(MODEL_PATH) and not force_retrain:
        print(f"Loading existing model from: {MODEL_PATH}")
        _MODEL_CACHE = joblib.load(MODEL_PATH)
        return _MODEL_CACHE
    
    if df is None:
        df = load_or_create_dataset(dataset_path)
    
    print("\nTraining model...")
    
    # Ensure all domain columns exist
    for domain in DOMAINS:
        if domain not in df.columns:
            raise ValueError(
                f"Dataset is missing required domain column '{domain}'. "
                "Enable generic adaptation or provide a mapped dataset."
            )
    
    label_col = detect_label_column(df)
    if label_col is None:
        df["predicted_domain"] = df[DOMAINS].idxmax(axis=1)
        label_col = "predicted_domain"
    elif label_col != "predicted_domain":
        df = df.rename(columns={label_col: "predicted_domain"})

    X = df[DOMAINS].values
    y = df["predicted_domain"].values

    # If any class has fewer than 2 samples, skip stratification to avoid ValueError
    _, class_counts = np.unique(y, return_counts=True)
    stratify_labels = y if class_counts.min() >= 2 else None

    if stratify_labels is None:
        print("Warning: Some classes have fewer than 2 samples; training without stratified split.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify_labels
    )
    
    model = RandomForestClassifier(n_estimators=150, random_state=42, max_depth=10)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Validation Accuracy: {accuracy:.2%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, digits=2, zero_division=0))
    
    # Save model
    joblib.dump(model, MODEL_PATH)
    _MODEL_CACHE = model
    print(f"Model saved to: {MODEL_PATH}")
    
    return model


# ===============================================================
# Function: Predict Interest
# ===============================================================
def predict_interest(user_scores: dict, model=None, dataset_path: str | None = None):
    """
    Predicts the primary interest domain for a user.

    Args:
        user_scores (dict): Dictionary of domain -> score (1-10).
        model: Trained classifier (loads from file if None).
        dataset_path (str | None): Optional dataset path override if model missing.

    Returns:
        dict: Prediction results with confidence scores.
    """
    global _MODEL_CACHE

    if model is None:
        if _MODEL_CACHE is not None:
            model = _MODEL_CACHE
        elif os.path.exists(MODEL_PATH):
            model = joblib.load(MODEL_PATH)
            _MODEL_CACHE = model
        else:
            model = train_model(dataset_path=dataset_path)
    
    # Create feature vector
    X_user = np.array([user_scores.get(d, 5) for d in DOMAINS]).reshape(1, -1)
    
    # Predict
    prediction = model.predict(X_user)[0]
    probabilities = model.predict_proba(X_user)[0]
    
    # Create probability mapping
    prob_dict = dict(zip(model.classes_, probabilities))
    
    # Sort by confidence
    sorted_probs = sorted(prob_dict.items(), key=lambda x: -x[1])

    # Identify top 2 interests based on user-given ratings
    sorted_by_score = sorted(user_scores.items(), key=lambda x: -x[1])
    top_2_by_rating = sorted_by_score[:2]

    return {
        "primary_interest": prediction,
        "predicted_interest": prediction,
        "confidence": float(prob_dict[prediction]),
        "all_probabilities": {k: round(float(v), 4) for k, v in sorted_probs},
        "top_3_interests": [
            {"domain": k, "confidence": round(float(v), 4)}
            for k, v in sorted_probs[:3]
        ],
        "top_2_interests": [
            {
                "domain": domain,
                "rating": int(score),
                "model_confidence": round(float(prob_dict.get(domain, 0)), 4),
            }
            for domain, score in top_2_by_rating
        ],
        "user_scores": {d: int(s) for d, s in user_scores.items()},
    }




    # All domain values for transparency
    all_values = []
    for domain in DOMAINS:
        score = user_scores.get(domain, 0)
        prob = all_probs.get(domain, 0)
        all_values.append({
            "domain": domain,
            "user_rating": int(score),
            "model_confidence": round(float(prob), 4),
            "model_confidence_percent": f"{prob * 100:.1f}%",
        })
    all_values.sort(key=lambda x: -x["user_rating"])

    return {
        "message": (
            f"Your top 2 interests are '{comparisons[0]['domain']}' "
            f"(rating: {comparisons[0]['user_rating']}/10) and "
            f"'{comparisons[1]['domain']}' "
            f"(rating: {comparisons[1]['user_rating']}/10). "
            f"Which one do you prefer? Here are detailed career paths for both."
        ),
        "question": "Which of these two interests do you prefer more?",
        "option_1": comparisons[0],
        "option_2": comparisons[1],
        "all_domain_values": all_values,
    }


# ===============================================================
# NOTE: Static per-domain catalogs removed.
# The legacy `_get_recommendation_for_domain` (hardcoded courses / resources /
# projects) and the legacy `generate_recommendations` (which built career data
# from the undefined `CAREER_PATHS` table) have been deleted. Roadmaps, courses,
# careers, and resume content are now generated dynamically by the OpenAI
# learning-path API — see the live `generate_recommendations` below and
# `advanced_learning_path.engine` / `openai_path_generator`.
# ===============================================================


# ===============================================================
# Function: Save Student Response
# ===============================================================
def save_student_response(user_info: dict, user_scores: dict, prediction: dict) -> str:
    """
    Saves student response and prediction to CSV.

    Args:
        user_info (dict): Student information (name, goals, etc.).
        user_scores (dict): Interest scores.
        prediction (dict): Prediction results.

    Returns:
        str: Path to saved file.
    """
    student_data = {
        **user_scores,
        "name": user_info.get("name", "Unknown"),
        "email": user_info.get("email", ""),
        "known_skills": user_info.get("known", ""),
        "want_to_learn": user_info.get("want", ""),
        "goals": user_info.get("goals", ""),
        "predicted_domain": prediction["primary_interest"],
        "confidence": prediction["confidence"],
        "timestamp": pd.Timestamp.now().isoformat()
    }
    
    # Append to master file
    master_file = os.path.join(OUTPUT_DIR, "all_student_responses.csv")
    df_new = pd.DataFrame([student_data])
    
    if os.path.exists(master_file):
        df_existing = pd.read_csv(master_file)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    
    df_combined.to_csv(master_file, index=False)
    
    # Also save individual file
    safe_name = user_info.get("name", "student").replace(" ", "_")
    individual_file = os.path.join(OUTPUT_DIR, f"{safe_name}_response.csv")
    df_new.to_csv(individual_file, index=False)
    
    return master_file


# ===============================================================
# Function: Generate Interest Chart
# ===============================================================
def generate_interest_chart(user_scores: dict, user_name: str = "Student") -> str:
    """
    Generates and saves an interest level bar chart.

    Args:
        user_scores (dict): Interest scores by domain.
        user_name (str): Name for the chart title.

    Returns:
        str: Path to saved chart image.
    """
    plt.figure(figsize=(10, 6))
    
    domains = list(user_scores.keys())
    values = list(user_scores.values())
    
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(domains)))
    bars = plt.bar(domains, values, color=colors, edgecolor="black")
    
    # Add value labels on bars
    for bar, val in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, 
                 str(val), ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.ylim(0, 11)
    plt.ylabel("Interest Level (1–10)", fontsize=12)
    plt.xlabel("Learning Domains", fontsize=12)
    plt.title(f"{user_name}'s Interest Profile", fontsize=14, fontweight='bold')
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    
    # Add grid
    plt.grid(axis='y', alpha=0.3)
    
    safe_name = user_name.replace(" ", "_")
    chart_path = os.path.join(OUTPUT_DIR, f"{safe_name}_interest_chart.png")
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


# ===============================================================
# Main CLI Interface
# ===============================================================
def run_cli():
    """
    Runs the command-line interface for the interest assessment.
    """
    print("=" * 60)
    print("   PERSONALIZED LEARNING PATH GENERATOR")
    print("   Interest Assessment Module")
    print("=" * 60)
    
    # Load or train model
    dataset_path = DATASET_OVERRIDE or DATASET_PATH
    model = train_model(dataset_path=dataset_path)
    
    # Collect user info
    print("\n--- Student Information ---")
    name = input("Enter your name: ").strip()
    email = input("Enter your email: ").strip()
    known = input("What do you already know? (brief): ").strip()
    want = input("What do you want to learn? (brief): ").strip()
    goals = input("What are your learning goals? (brief): ").strip()
    
    user_info = {
        "name": name,
        "email": email,
        "known": known,
        "want": want,
        "goals": goals
    }
    
    # Collect interest scores
    print("\n--- Interest Assessment ---")
    print("Rate your interest in each domain (1 = low, 10 = high):\n")
    
    user_scores = {}
    for domain in DOMAINS:
        while True:
            try:
                rating = int(input(f"  {domain}: ").strip())
                if 1 <= rating <= 10:
                    user_scores[domain] = rating
                    break
                else:
                    print("  Please enter a number between 1 and 10.")
            except ValueError:
                print("  Invalid input. Enter a numeric value between 1 and 10.")
    
    # Make prediction
    prediction = predict_interest(user_scores, model)
    
    # Generate recommendations
    recommendations = generate_recommendations(prediction, user_info)
    
    # Generate top 2 comparison
    comparison = generate_top_interests_comparison(prediction, user_info)
    
    # Display results
    print("\n" + "=" * 60)
    print("   YOUR PERSONALIZED LEARNING PATH")
    print("=" * 60)
    
    print(f"\n🎯 Primary Interest: {recommendations['primary_interest']}")
    print(f"   Confidence: {recommendations['confidence']:.1%}")
    print(f"\n📝 {recommendations['description']}")
    
    print("\n📚 Recommended Courses:")
    for course in recommendations['recommended_courses']:
        print(f"   • {course}")
    
    print("\n🔗 Helpful Resources:")
    for resource in recommendations['resources']:
        print(f"   • {resource}")
    
    print("\n💻 Suggested Projects:")
    for project in recommendations['suggested_projects']:
        print(f"   • {project}")
    
    if recommendations['secondary_interests']:
        print(f"\n🔄 Secondary Interests: {', '.join(recommendations['secondary_interests'])}")
    
    # Show top 2 interests comparison
    if "error" not in comparison:
        print("\n" + "=" * 60)
        print("   YOUR TOP 2 INTERESTS COMPARISON")
        print("=" * 60)
        print(f"\n📊 {comparison['message']}")
        print(f"\n❓ {comparison['question']}")
        
        for i, key in enumerate(["option_1", "option_2"], 1):
            opt = comparison[key]
            print(f"\n--- Option {i}: {opt['domain']} ---")
            print(f"   Your Rating: {opt['user_rating']}/10")
            print(f"   Model Confidence: {opt['model_confidence_percent']}")
            print(f"   {opt['description']}")
            
            career = opt["career_path"]
            print(f"\n   Career Options: {', '.join(career['career_options'])}")
            print(f"   Salary Range: {career['average_salary_range']}")
            print(f"   Growth Outlook: {career['growth_outlook']}")
            print(f"   Skills Needed: {', '.join(career['skills_needed'])}")
            print(f"   Next Steps:")
            for step in career["next_steps"]:
                print(f"      • {step}")
        
        # Show all domain values
        print("\n" + "-" * 40)
        print("   ALL DOMAIN VALUES (Accurate)")
        print("-" * 40)
        for v in comparison["all_domain_values"]:
            print(f"   {v['domain']}: Rating={v['user_rating']}/10, "
                  f"Confidence={v['model_confidence_percent']}")
        
        # Ask user to choose
        print()
        choice = input(f"Which do you prefer? (1 = {comparison['option_1']['domain']}, "
                       f"2 = {comparison['option_2']['domain']}): ").strip()
        
        if choice == "1":
            chosen = comparison["option_1"]
        elif choice == "2":
            chosen = comparison["option_2"]
        else:
            chosen = comparison["option_1"]
            print("  Invalid choice. Defaulting to Option 1.")
        
        print(f"\n🎉 You chose: {chosen['domain']}")
        print(f"   Follow the career path and next steps above to get started!")
    
    # Save results
    save_student_response(user_info, user_scores, prediction)
    chart_path = generate_interest_chart(user_scores, name)
    
    print(f"\n✅ Results saved!")
    print(f"   Chart: {chart_path}")
    print("\n" + "=" * 60)


# ===============================================================
# Entry Point
# ===============================================================
if __name__ == "__main__" and os.getenv("USE_LEGACY_PERSONALIZED_LEARNING_PATH", "false").lower() == "true":
    run_cli()


# ==============================================================================
# Advanced, compatibility-safe override layer
# ==============================================================================
from advanced_learning_path import AdvancedLearningPathEngine
from advanced_learning_path.charts import generate_domain_comparison, generate_growth_graph, generate_radar_chart, generate_skill_heatmap
from advanced_learning_path.storage import LearningPathRepository

import logging
logger = logging.getLogger(__name__)

try:
    from xgboost import XGBClassifier  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    XGBClassifier = None

_ADV_ENGINE = AdvancedLearningPathEngine()
_ADV_REPOSITORY = LearningPathRepository()


class HybridInterestModel:
    """Thin wrapper around an sklearn classifier with metadata for persistence."""

    def __init__(self, classifier, feature_names, domains):
        self.classifier = classifier
        self.feature_names = feature_names
        self.classes_ = getattr(classifier, "classes_", np.array(domains))
        self.domains = domains

    def predict(self, X):
        return self.classifier.predict(X)

    def predict_proba(self, X):
        if hasattr(self.classifier, "predict_proba"):
            return self.classifier.predict_proba(X)
        # deterministic fallback if the classifier has no proba
        preds = self.classifier.predict(X)
        matrix = np.zeros((len(preds), len(self.classes_)), dtype=float)
        for row_idx, pred in enumerate(preds):
            if pred in self.classes_:
                matrix[row_idx, list(self.classes_).index(pred)] = 1.0
        return matrix



def _build_hybrid_classifier():
    """Build an ensemble model with graceful fallbacks."""
    from sklearn.ensemble import RandomForestClassifier, VotingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    estimators = []

    rf = RandomForestClassifier(
        n_estimators=250,
        max_depth=14,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )
    estimators.append(("rf", rf))

    lr = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "lr",
                LogisticRegression(
                    max_iter=4000,
                    class_weight="balanced",
                ),
            ),
        ]
    )
    estimators.append(("lr", lr))

    if XGBClassifier is not None:
        try:
            xgb = XGBClassifier(
                n_estimators=180,
                max_depth=5,
                learning_rate=0.06,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="multi:softprob",
                eval_metric="mlogloss",
                random_state=42,
                tree_method="hist",
                verbosity=0,
            )
            estimators.append(("xgb", xgb))
        except Exception as exc:
            logger.warning("XGBoost unavailable, continuing with RF+LR only: %s", exc)

    if len(estimators) == 1:
        return estimators[0][1]

    return VotingClassifier(estimators=estimators, voting="soft", weights=[3, 2] + ([2] if len(estimators) == 3 else []), n_jobs=-1)



def _ensure_domain_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = []
    for domain in DOMAINS:
        if domain not in df.columns:
            missing.append(domain)
    if missing:
        raise ValueError(
            "Dataset is missing required domain columns after preprocessing: "
            + ", ".join(missing)
        )
    return df



def _normalize_scores(user_scores: dict) -> dict:
    normalized = {}
    for domain in DOMAINS:
        try:
            normalized[domain] = int(user_scores.get(domain, 0))
        except (TypeError, ValueError):
            normalized[domain] = 0
    return normalized



def _ml_probabilities(model, user_scores: dict) -> dict:
    X_user = np.array([user_scores.get(d, 0) for d in DOMAINS]).reshape(1, -1)
    predicted = model.predict(X_user)[0]
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_user)[0]
        prob_dict = {domain: float(prob) for domain, prob in zip(model.classes_, proba)}
    else:
        prob_dict = {domain: 0.0 for domain in DOMAINS}
        prob_dict[predicted] = 1.0
    return {domain: float(prob_dict.get(domain, 0.0)) for domain in DOMAINS}


def get_ml_probability_scores(user_scores: dict) -> dict:
    """Return per-domain ML probabilities on a 0-100 scale without OpenAI calls."""
    global _MODEL_CACHE

    sanitized = _normalize_scores(user_scores)
    model = None
    if _MODEL_CACHE is not None:
        model = _MODEL_CACHE
    elif os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            _MODEL_CACHE = model
        except Exception:
            model = train_model()
    else:
        model = train_model()

    if isinstance(model, dict) and "classifier" in model:
        model = HybridInterestModel(model["classifier"], DOMAINS, DOMAINS)

    ml_probs = _ml_probabilities(model, sanitized)
    return {domain: round(float(ml_probs.get(domain, 0.0)) * 100.0, 2) for domain in DOMAINS}



def _combine_hybrid_scores(ml_probs: dict, advanced_probs: dict) -> dict:
    combined = {}
    for domain in DOMAINS:
        ml = float(ml_probs.get(domain, 0.0))
        adv = float(advanced_probs.get(domain, 0.0)) / 100.0
        # Weighted average leans slightly toward the ML model while using the advanced engine for context.
        combined[domain] = round(min(1.0, (0.58 * ml) + (0.42 * adv)), 6)
    return combined



def train_model(df: pd.DataFrame = None, force_retrain: bool = False, dataset_path: str | None = None):
    """Train the hybrid model with RF + optional XGBoost + logistic regression voting."""
    global _MODEL_CACHE
    target_dataset = _resolve_dataset_path(dataset_path)
    needs_refresh = AUTO_RETRAIN_ON_DATASET_CHANGE and _dataset_newer_than_model(target_dataset)

    if needs_refresh and not force_retrain:
        logger.info(
            "Dataset changed after model build. Auto-retraining from: %s",
            target_dataset,
        )
        force_retrain = True

    if _MODEL_CACHE is not None and not force_retrain:
        return _MODEL_CACHE

    if os.path.exists(MODEL_PATH) and not force_retrain:
        try:
            logger.info(f"Loading existing model from: {MODEL_PATH}")
            _MODEL_CACHE = joblib.load(MODEL_PATH)
            return _MODEL_CACHE
        except Exception as exc:
            logger.warning(f"Failed to load existing model, retraining: {exc}")

    if df is None:
        df = load_or_create_dataset(target_dataset)

    df = _ensure_domain_columns(df.copy())

    label_col = detect_label_column(df)
    if label_col is None:
        df["predicted_domain"] = df[DOMAINS].idxmax(axis=1)
        label_col = "predicted_domain"
    elif label_col != "predicted_domain":
        df = df.rename(columns={label_col: "predicted_domain"})

    X = df[DOMAINS].values
    y = df["predicted_domain"].values

    _, class_counts = np.unique(y, return_counts=True)
    stratify_labels = y if class_counts.min() >= 2 else None

    if stratify_labels is None:
        logger.warning("Some classes have fewer than 2 samples; training without stratified split.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify_labels
    )

    classifier = _build_hybrid_classifier()
    classifier.fit(X_train, y_train)

    y_pred = classifier.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logger.info("Hybrid model validation accuracy: %.2f%%", accuracy * 100)
    logger.info("\n%s", classification_report(y_test, y_pred, digits=2, zero_division=0))

    bundle = HybridInterestModel(classifier=classifier, feature_names=DOMAINS, domains=DOMAINS)
    joblib.dump(bundle, MODEL_PATH)
    _MODEL_CACHE = bundle
    logger.info(f"Hybrid model saved to: {MODEL_PATH}")
    return bundle



def predict_interest(user_scores: dict, model=None, dataset_path: str | None = None):
    """Predict the primary interest using the hybrid ML + intelligence engine."""
    global _MODEL_CACHE

    sanitized_scores = _normalize_scores(user_scores)

    if model is None:
        if _MODEL_CACHE is not None:
            model = _MODEL_CACHE
        elif os.path.exists(MODEL_PATH):
            try:
                model = joblib.load(MODEL_PATH)
                _MODEL_CACHE = model
            except Exception:
                model = train_model(dataset_path=dataset_path)
        else:
            model = train_model(dataset_path=dataset_path)

    if isinstance(model, dict) and "classifier" in model:
        model = HybridInterestModel(model["classifier"], DOMAINS, DOMAINS)

    ml_probs = _ml_probabilities(model, sanitized_scores)

    advanced_result = _ADV_ENGINE.predict_interest({"scores": sanitized_scores})
    advanced_probs = advanced_result.get("all_probabilities", {})
    hybrid_probs = _combine_hybrid_scores(ml_probs, advanced_probs)

    primary = max(hybrid_probs.items(), key=lambda item: item[1])[0]
    confidence = float(hybrid_probs[primary])
    model_confidence = float(ml_probs.get(primary, confidence))

    ranked = sorted(hybrid_probs.items(), key=lambda item: item[1], reverse=True)
    top_3 = [
        {
            "domain": domain,
            "confidence": round(prob, 6),
            "model_confidence": round(float(ml_probs.get(domain, 0.0)), 6),
            "why_matched": advanced_result.get("top_3_interests", [{}])[idx].get("why_matched", []) if idx < len(advanced_result.get("top_3_interests", [])) else [],
        }
        for idx, (domain, prob) in enumerate(ranked[:3])
    ]

    top_2 = [
        {
            "domain": domain,
            "rating": int(sanitized_scores.get(domain, 0)),
            "model_confidence": round(float(ml_probs.get(domain, 0.0)), 6),
        }
        for domain, _ in ranked[:2]
    ]

    return {
        "primary_interest": primary,
        "predicted_interest": primary,
        "confidence": confidence,
        "model_confidence": model_confidence,
        "all_probabilities": {d: round(float(p), 6) for d, p in hybrid_probs.items()},
        "top_3_interests": top_3,
        "top_2_interests": top_2,
        "user_scores": sanitized_scores,
        "user_profile": advanced_result.get("user_profile"),
        "roadmap": advanced_result.get("roadmap"),
        "career_paths": advanced_result.get("career_paths"),
        "skills_gap": advanced_result.get("skills_gap"),
        "projects": advanced_result.get("projects"),
        "certifications": advanced_result.get("certifications"),
        "gamification": advanced_result.get("gamification"),
        "visual_analytics": advanced_result.get("visual_analytics"),
        "signals": advanced_result.get("signals"),
        "metadata": advanced_result.get("metadata"),
        "source": "hybrid-intelligence",
    }



def generate_recommendations(prediction: dict, user_info: dict = None) -> dict:
    """Generate recommendations with dynamic roadmap, courses, and careers from the API."""
    user_info = user_info or {}
    scores = prediction.get("user_scores", {})
    primary = prediction.get("primary_interest", DOMAINS[0])
    current_top = prediction.get("top_3_interests", [])
    secondary = [item["domain"] for item in current_top[1:]] if len(current_top) > 1 else []

    path_result = _ADV_ENGINE.generate_roadmap(
        primary,
        {"scores": scores, "user": user_info, "secondary_domains": secondary},
    )
    roadmap = path_result.get("roadmap") or {}
    careers_detailed = path_result.get("careers_detailed") or []
    courses = ((roadmap.get("resources") or {}).get("courses") or [])
    projects = roadmap.get("suggested_projects") or []

    topic_roadmap = {
        "Beginner": (roadmap.get("beginner") or {}).get("topics") or [],
        "Intermediate": (roadmap.get("intermediate") or {}).get("topics") or [],
        "Advanced": (roadmap.get("advanced") or {}).get("topics") or [],
    }
    stage_project_roadmap = {
        "Beginner": (roadmap.get("beginner") or {}).get("stage_projects") or [],
        "Intermediate": (roadmap.get("intermediate") or {}).get("stage_projects") or [],
        "Advanced": (roadmap.get("advanced") or {}).get("stage_projects") or [],
    }

    career_roles = [c.get("title") for c in careers_detailed if c.get("title")]
    primary_career = {
        "roles": career_roles,
        "career_options": career_roles,
        "careers_detailed": careers_detailed,
    }

    return {
        "primary_interest": primary,
        "confidence": float(prediction.get("confidence", 0.0)),
        "description": f"Personalized {primary} path generated dynamically from your profile and quiz caliber.",
        "recommended_courses": courses,
        "advanced_courses": [],
        "resources": courses,
        "advanced_resources": [],
        "suggested_projects": projects,
        "advanced_projects": [],
        "topic_roadmap": topic_roadmap,
        "stage_project_roadmap": stage_project_roadmap,
        "secondary_interests": secondary,
        "learning_approach": {
            "type": "adaptive",
            "message": "Roadmap, courses, and careers are generated live by the OpenAI learning-path API.",
            "suggestions": [
                "Follow the beginner roadmap first",
                "Use projects to validate every new concept",
                "Take quizzes at your recommended difficulty",
                "Review skill gaps before jumping to advanced topics",
            ],
        },
        "is_physical_domain": primary == "Physical Games / Sports",
        "career_path": primary_career,
        "careers_detailed": careers_detailed,
        "roadmap": roadmap,
        "skills_gap": path_result.get("skills_gap", {}),
        "projects": [{"domain": primary, "project": p, "difficulty": "progressive"} for p in projects[:9]],
        "certifications": [],
        "gamification": prediction.get("gamification", {}),
        "visual_analytics": prediction.get("visual_analytics", {}),
        "user_info": user_info,
        "resume_outline": path_result.get("resume_outline"),
        "recommended_quiz_difficulty": path_result.get("recommended_quiz_difficulty"),
        "caliber_summary": path_result.get("caliber_summary"),
    }



def generate_top_interests_comparison(prediction_result: dict, user_info: dict = None) -> dict:
    """Compare the top 2 domains using the new signal-rich engine."""
    user_info = user_info or {}
    top_2 = prediction_result.get("top_2_interests", [])
    if len(top_2) < 2:
        return {"error": "Not enough interests to compare."}

    comparisons = []
    for item in top_2:
        domain = item["domain"]
        insight = _ADV_ENGINE.get_recommendations({"scores": {domain: 10}, "user": user_info})
        comparison_entry = {
            "domain": domain,
            "user_rating": item.get("rating", 0),
            "model_confidence": item.get("model_confidence", 0),
            "model_confidence_percent": f"{item.get('model_confidence', 0) * 100:.1f}%",
            "description": insight["recommendations"][0].get("why_matched", [f"Strong match for {domain}"])[0] if insight.get("recommendations") else f"Strong match for {domain}",
            "career_path": insight["career_paths"].get(domain, {}),
            "recommended_courses": insight["recommendations"][0].get("best_courses", []) if insight.get("recommendations") else [],
            "resources": insight["recommendations"][0].get("community_resources", []) if insight.get("recommendations") else [],
            "suggested_projects": insight["recommendations"][0].get("best_projects", []) if insight.get("recommendations") else [],
        }
        comparisons.append(comparison_entry)

    all_values = []
    all_probs = prediction_result.get("all_probabilities", {})
    user_scores = prediction_result.get("user_scores", {})
    for domain in DOMAINS:
        score = user_scores.get(domain, 0)
        prob = all_probs.get(domain, 0)
        all_values.append({
            "domain": domain,
            "user_rating": int(score),
            "model_confidence": round(float(prob), 6),
            "model_confidence_percent": f"{prob * 100:.1f}%",
        })
    all_values.sort(key=lambda x: -x["user_rating"])

    return {
        "message": (
            f"Your top 2 interests are '{comparisons[0]['domain']}' and '{comparisons[1]['domain']}'. "
            f"The advanced engine suggests a tie-breaker based on your goals, skills, and engagement patterns."
        ),
        "question": "Which of these two interests do you prefer more?",
        "option_1": comparisons[0],
        "option_2": comparisons[1],
        "all_domain_values": all_values,
    }



def save_student_response(user_info: dict, user_scores: dict, prediction: dict) -> str:
    """Persist assessment to CSV for backward compatibility and to SQLite for production storage."""
    from pathlib import Path
    import pandas as pd

    user_info = user_info or {}
    student_data = {
        **_normalize_scores(user_scores),
        "name": user_info.get("name", "Unknown"),
        "email": user_info.get("email", ""),
        "known_skills": user_info.get("known", ""),
        "want_to_learn": user_info.get("want", ""),
        "goals": user_info.get("goals", ""),
        "predicted_domain": prediction["primary_interest"],
        "confidence": prediction["confidence"],
        "model_confidence": prediction.get("model_confidence", prediction["confidence"]),
        "timestamp": pd.Timestamp.now().isoformat(),
    }

    master_file = os.path.join(OUTPUT_DIR, "all_student_responses.csv")
    df_new = pd.DataFrame([student_data])
    if os.path.exists(master_file):
        df_existing = pd.read_csv(master_file)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    df_combined.to_csv(master_file, index=False)

    safe_name = user_info.get("name", "student").replace(" ", "_")
    individual_file = os.path.join(OUTPUT_DIR, f"{safe_name}_response.csv")
    df_new.to_csv(individual_file, index=False)

    # Also persist to sqlite if we can infer an id
    try:
        payload = {
            "name": user_info.get("name"),
            "full_name": user_info.get("name"),
            "email": user_info.get("email"),
            "learning_level": user_info.get("learning_level"),
            "learning_style": user_info.get("learning_style") or user_info.get("contentFormat"),
            "weekly_availability_hours": user_info.get("weekly_availability_hours"),
            "personality": user_info.get("personality"),
        }
        if user_info.get("email"):
            _ADV_REPOSITORY.upsert_user(user_info["email"], payload)
            _ADV_REPOSITORY.save_assessment(user_info["email"], {"scores": _normalize_scores(user_scores), "user": user_info}, prediction.get("signals", {}), prediction)
            _ADV_REPOSITORY.save_prediction(user_info["email"], prediction["primary_interest"], prediction, {"confidence": prediction.get("model_confidence", prediction["confidence"]), "hybrid": prediction["confidence"]}, prediction.get("top_3_interests", []))
    except Exception as exc:
        logger.warning("SQLite persistence failed (CSV still saved): %s", exc)

    return master_file



def generate_interest_chart(user_scores: dict, user_name: str = "Student") -> str:
    """Generate radar + comparison charts for the learning profile."""
    scores = _normalize_scores(user_scores)
    visuals_dir = os.path.join(OUTPUT_DIR, "visuals")
    radar = generate_radar_chart(scores, user_name, visuals_dir)
    # create a simple comparison/heatmap based on the current scores so the UI can choose which to show
    comparison = generate_domain_comparison(scores, user_name, visuals_dir)
    try:
        labels = list(scores.keys())
        matrix = [[scores[a] if a == b else abs(scores[a] - scores[b]) for b in labels] for a in labels]
        generate_skill_heatmap(matrix, labels, user_name, visuals_dir)
    except Exception as exc:
        logger.warning("Heatmap generation failed: %s", exc)
    try:
        history = [{"domain": d, "score": s} for d, s in scores.items()]
        generate_growth_graph(history, user_name, visuals_dir)
    except Exception as exc:
        logger.warning("Growth graph generation failed: %s", exc)
    return radar



def generate_learning_roadmap(domain: str, user_info: dict = None, user_scores: dict = None) -> dict:
    """Expose roadmap generation as a dedicated helper for API consumers."""
    payload = {"scores": user_scores or {}, "user": user_info or {}}
    return _ADV_ENGINE.generate_roadmap(domain, payload)



def get_user_profile_summary(user_info: dict, user_scores: dict) -> dict:
    """Return the structured JSON output requested by the product brief."""
    prediction = predict_interest(user_scores, model=None)
    recommendations = generate_recommendations(prediction, user_info)
    return {
        "user_profile": prediction.get("user_profile"),
        "top_domains": prediction.get("top_3_interests", []),
        "confidence_scores": prediction.get("all_probabilities", {}),
        "roadmap": recommendations.get("roadmap", {}),
        "career_paths": recommendations.get("career_path", {}),
        "skills_gap": recommendations.get("skills_gap", {}),
        "projects": recommendations.get("projects", []),
        "certifications": recommendations.get("certifications", []),
        "gamification": recommendations.get("gamification", {}),
    }



def run_cli():
    """Run the upgraded CLI with advanced intelligence and rich analytics."""
    print("=" * 70)
    print("  PERSONALIZED LEARNING PATH GENERATOR — ADVANCED EDITION")
    print("=" * 70)

    dataset_path = DATASET_OVERRIDE or DATASET_PATH
    model = train_model(dataset_path=dataset_path)

    print("\n--- Student Information ---")
    name = input("Enter your name: ").strip()
    email = input("Enter your email: ").strip()
    known = input("What do you already know? (brief): ").strip()
    want = input("What do you want to learn? (brief): ").strip()
    goals = input("What are your learning goals? (brief): ").strip()
    learning_style = input("Preferred learning style (project-based / visual / self-paced / mixed): ").strip()
    weekly_hours = input("Hours available per week: ").strip()
    confidence_level = input("Confidence in your answers (0-1, optional): ").strip()

    user_info = {
        "name": name,
        "email": email,
        "known": known,
        "want": want,
        "goals": goals,
        "learning_style": learning_style,
        "weekly_availability_hours": int(weekly_hours) if weekly_hours.isdigit() else 5,
        "confidence_level": float(confidence_level) if confidence_level else 0.7,
        "current_skills": [x.strip() for x in known.split(",") if x.strip()],
        "learning_goals": [x.strip() for x in goals.split(",") if x.strip()],
        "personality": "explorer",
    }

    print("\n--- Interest Assessment ---")
    print("Rate your interest in each domain (1 = low, 10 = high):\n")
    user_scores = {}
    for domain in DOMAINS:
        while True:
            try:
                rating = int(input(f"  {domain}: ").strip())
                if 1 <= rating <= 10:
                    user_scores[domain] = rating
                    break
                print("  Please enter a number between 1 and 10.")
            except ValueError:
                print("  Invalid input. Enter a numeric value between 1 and 10.")

    prediction = predict_interest(user_scores, model)
    recommendations = generate_recommendations(prediction, user_info)
    comparison = generate_top_interests_comparison(prediction, user_info)
    profile_summary = get_user_profile_summary(user_info, user_scores)

    print("\n" + "=" * 70)
    print("  YOUR PERSONALIZED LEARNING PATH")
    print("=" * 70)
    print(f"\n🎯 Primary Interest: {recommendations['primary_interest']}")
    print(f"   Confidence: {recommendations['confidence']:.1%}")
    print(f"   Model Confidence: {prediction.get('model_confidence', 0):.1%}")
    print(f"   User Profile: {profile_summary['user_profile']}")

    print("\n📚 Recommended Courses:")
    for course in recommendations['recommended_courses'][:5]:
        print(f"   • {course}")

    print("\n🔗 Helpful Resources:")
    for resource in recommendations['resources'][:5]:
        print(f"   • {resource}")

    print("\n💻 Suggested Projects:")
    for project in recommendations['suggested_projects'][:5]:
        print(f"   • {project}")

    if recommendations['secondary_interests']:
        print(f"\n🔄 Secondary Interests: {', '.join(recommendations['secondary_interests'])}")

    print("\n📈 Gamification:")
    print(f"   Level: {recommendations.get('gamification', {}).get('level', 1)}")
    print(f"   XP: {recommendations.get('gamification', {}).get('xp', 0)}")
    print(f"   Streak: {recommendations.get('gamification', {}).get('streak_days', 0)} days")

    if "error" not in comparison:
        print("\n" + "=" * 70)
        print("  YOUR TOP 2 INTERESTS COMPARISON")
        print("=" * 70)
        print(f"\n📊 {comparison['message']}")
        print(f"\n❓ {comparison['question']}")
        for i, key in enumerate(["option_1", "option_2"], 1):
            opt = comparison[key]
            print(f"\n--- Option {i}: {opt['domain']} ---")
            print(f"   Your Rating: {opt['user_rating']}/10")
            print(f"   Model Confidence: {opt['model_confidence_percent']}")
            print(f"   {opt['description']}")
            career = opt["career_path"]
            print(f"\n   Career Roles: {', '.join(career.get('roles', career.get('career_options', [])))}")
            print(f"   Salary Range: {career.get('salary_range', career.get('average_salary_range', 'N/A'))}")
            print(f"   Market Demand: {career.get('market_demand', 'N/A')}")
            print(f"   Required Tools: {', '.join(career.get('required_tools', career.get('skills_needed', [])))}")
            print("   Next Steps:")
            for step in career.get('next_steps', []):
                print(f"      • {step}")

    save_student_response(user_info, user_scores, prediction)
    chart_path = generate_interest_chart(user_scores, name)

    print("\n✅ Results saved!")
    print(f"   Chart: {chart_path}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_cli()

