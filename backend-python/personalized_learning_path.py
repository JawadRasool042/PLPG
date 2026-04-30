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

# Heavy ML libraries are imported lazily (inside functions) to speed up startup.
# They will be loaded on first use only.
_np = None
_pd = None
_plt = None
_joblib = None
_sklearn_loaded = False

def _load_ml_libs():
    """Lazy-load all heavy ML libraries on first use."""
    global _np, _pd, _plt, _joblib, _sklearn_loaded
    if _sklearn_loaded:
        return
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import joblib
    _np = np
    _pd = pd
    _plt = plt
    _joblib = joblib
    _sklearn_loaded = True


# ===============================================================
# Configuration
# ===============================================================
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "interest_model.joblib")
DATASET_PATH = os.path.join(os.path.dirname(__file__), "data", "student_interests.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "student_results")
LABEL_CANDIDATES = ["predicted_domain", "label", "target", "interest_domain"]

# Allow overriding dataset via env for flexibility
DATASET_OVERRIDE = os.getenv("INTEREST_DATASET_PATH")

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

# Ensure directories exist
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cache the loaded model in-memory for API performance
_MODEL_CACHE = None


# ===============================================================
# Function: Generate Synthetic Dataset
# ===============================================================
def generate_synthetic_dataset(domains: list, samples: int = 1000):
    _load_ml_libs()
    np = _np
    pd = _pd

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
def detect_label_column(df) -> str | None:
    """Return the first matching label column name or None."""
    for cand in LABEL_CANDIDATES:
        if cand in df.columns:
            return cand
    return None


# ===============================================================
# Function: Load Dataset from CSV (manual loader)
# ===============================================================
def load_dataset_from_csv(csv_path: str, domains: list):
    _load_ml_libs()
    pd = _pd

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8")
    missing = [d for d in domains if d not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required domain columns: {missing}")

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
def load_or_create_dataset(dataset_path=None):
    _load_ml_libs()
    pd = _pd
    target_path = dataset_path or DATASET_OVERRIDE or DATASET_PATH

    try:
        print(f"Loading dataset from: {target_path}")
        df = load_dataset_from_csv(target_path, DOMAINS)
        print(f"Loaded {len(df)} records.")
        return df
    except FileNotFoundError:
        print(f"Dataset not found at {target_path}. Generating synthetic dataset...")
    except ValueError as e:
        print(f"Dataset validation failed ({e}). Falling back to synthetic data.")
    
    df = generate_synthetic_dataset(DOMAINS, samples=1000)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    df.to_csv(target_path, index=False)
    print(f"Synthetic dataset saved to: {target_path}")
    return df


# ===============================================================
# Function: Train Model
# ===============================================================
def train_model(df=None, force_retrain: bool = False, dataset_path=None):
    """Trains the interest prediction model."""
    _load_ml_libs()
    np = _np
    joblib = _joblib
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report

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
            df[domain] = np.random.randint(1, 11, size=len(df))
    
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
def predict_interest(user_scores: dict, model=None, dataset_path=None):
    """Predicts the primary interest domain for a user."""
    _load_ml_libs()
    np = _np
    joblib = _joblib

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
    
    return {
        "primary_interest": prediction,
        "confidence": float(prob_dict[prediction]),
        "all_probabilities": {k: round(float(v), 4) for k, v in sorted_probs},
        "top_3_interests": [
            {"domain": k, "confidence": round(float(v), 4)} 
            for k, v in sorted_probs[:3]
        ]
    }


# ===============================================================
# Function: Generate Recommendations
# ===============================================================
def generate_recommendations(prediction_result: dict, user_info: dict = None) -> dict:
    """
    Generates personalized learning recommendations based on prediction.

    Args:
        prediction_result (dict): Output from predict_interest().
        user_info (dict): Additional user information (name, goals, etc.).

    Returns:
        dict: Personalized recommendations.
    """
    primary = prediction_result["primary_interest"]
    
    # Recommendation database
    recommendations_db = {
        "Coding": {
            "description": "You have a strong interest in programming fundamentals and software development.",
            "courses": [
                "Python for Beginners - freeCodeCamp",
                "Java Programming Masterclass - Udemy",
                "C++ Programming Course - Coursera"
            ],
            "resources": [
                "LeetCode for practice problems",
                "HackerRank challenges",
                "Codecademy interactive courses"
            ],
            "projects": [
                "Build a calculator application",
                "Create a todo list manager",
                "Develop a simple game (Tic-Tac-Toe)"
            ]
        },
        "Web Development": {
            "description": "You're drawn to creating websites and web applications.",
            "courses": [
                "The Web Developer Bootcamp - Udemy",
                "Full Stack Open - University of Helsinki",
                "freeCodeCamp Web Development Path"
            ],
            "resources": [
                "MDN Web Docs",
                "CSS-Tricks",
                "JavaScript.info"
            ],
            "projects": [
                "Build a personal portfolio website",
                "Create a blog platform",
                "Develop an e-commerce store"
            ]
        },
        "Game Development": {
            "description": "You have a passion for creating interactive games and experiences.",
            "courses": [
                "Unity Game Development - Udemy",
                "Unreal Engine 5 Masterclass",
                "Godot Engine Tutorials"
            ],
            "resources": [
                "Unity Learn Platform",
                "GameDev.tv",
                "Brackeys YouTube Channel"
            ],
            "projects": [
                "Create a 2D platformer game",
                "Build a simple puzzle game",
                "Develop a multiplayer card game"
            ]
        },
        "Cybersecurity": {
            "description": "You're interested in security, ethical hacking, and protecting systems.",
            "courses": [
                "CompTIA Security+ Certification",
                "Ethical Hacking Course - Udemy",
                "Cybersecurity Specialization - Coursera"
            ],
            "resources": [
                "TryHackMe",
                "HackTheBox",
                "OWASP Resources"
            ],
            "projects": [
                "Set up a home lab for penetration testing",
                "Conduct a vulnerability assessment",
                "Build a network monitoring tool"
            ]
        },
        "Data Science": {
            "description": "You enjoy analyzing data and extracting insights from information.",
            "courses": [
                "Data Science Specialization - Coursera",
                "Python for Data Science - DataCamp",
                "Statistics for Data Science - edX"
            ],
            "resources": [
                "Kaggle Datasets & Competitions",
                "Towards Data Science Blog",
                "Analytics Vidhya"
            ],
            "projects": [
                "Analyze a public dataset (COVID, weather, etc.)",
                "Build a data visualization dashboard",
                "Create a predictive model for stock prices"
            ]
        },
        "Mobile Development": {
            "description": "You're interested in building apps for smartphones and tablets.",
            "courses": [
                "iOS Development with Swift - Udemy",
                "Android Development - Google",
                "React Native Course - Coursera"
            ],
            "resources": [
                "Apple Developer Documentation",
                "Android Developers Guide",
                "Flutter Documentation"
            ],
            "projects": [
                "Build a weather app",
                "Create a note-taking application",
                "Develop a fitness tracking app"
            ]
        },
        "Cloud Computing": {
            "description": "You're drawn to cloud platforms, DevOps, and infrastructure.",
            "courses": [
                "AWS Solutions Architect - Udemy",
                "Google Cloud Fundamentals - Coursera",
                "Azure Administrator Certification"
            ],
            "resources": [
                "AWS Free Tier",
                "Google Cloud Skills Boost",
                "Microsoft Learn"
            ],
            "projects": [
                "Deploy a web application to AWS",
                "Set up a CI/CD pipeline",
                "Create a serverless function"
            ]
        },
        "AI & Machine Learning": {
            "description": "You're fascinated by artificial intelligence and machine learning algorithms.",
            "courses": [
                "Machine Learning by Andrew Ng - Coursera",
                "Deep Learning Specialization - Coursera",
                "Fast.ai Practical Deep Learning"
            ],
            "resources": [
                "TensorFlow Documentation",
                "PyTorch Tutorials",
                "Papers With Code"
            ],
            "projects": [
                "Build an image classifier",
                "Create a chatbot using NLP",
                "Develop a recommendation system"
            ]
        },
        "Physical Games / Sports": {
            "description": "You have a strong interest in physical activities, sports, and fitness.",
            "courses": [
                "Sports Science Fundamentals - Coursera",
                "Coaching Certification Programs",
                "Physical Fitness Training - edX"
            ],
            "resources": [
                "Local sports clubs and associations",
                "Physical education coaching centers",
                "Fitness and athletic training apps"
            ],
            "projects": [
                "Join a local sports team or club",
                "Create a personal fitness training plan",
                "Organize community sports events"
            ],
            "is_physical": True
        }
    }
    
    rec = recommendations_db.get(primary, {
        "description": f"You have interest in {primary}.",
        "courses": ["Explore online courses on this topic"],
        "resources": ["Search for tutorials and documentation"],
        "projects": ["Start with beginner-friendly projects"]
    })
    
    # Special handling for Physical Games / Sports domain
    is_physical = rec.get("is_physical", False)
    
    # Build learning approach based on domain type
    if is_physical:
        learning_approach = {
            "type": "physical",
            "message": "Focus on physical practice, coaching sessions, and joining clubs.",
            "suggestions": [
                "Join local sports clubs and associations",
                "Find a personal coach or trainer",
                "Participate in community sports events",
                "Practice regularly with structured training",
                "Consider sports science certifications"
            ]
        }
    else:
        learning_approach = {
            "type": "digital",
            "message": "Explore online learning platforms with project-based and self-paced learning.",
            "suggestions": [
                "Practice with hands-on projects",
                "Join online communities and forums",
                "Follow structured learning paths",
                "Build a portfolio of projects"
            ]
        }
    
    return {
        "primary_interest": primary,
        "confidence": prediction_result["confidence"],
        "description": rec["description"],
        "recommended_courses": rec["courses"],
        "resources": rec["resources"],
        "suggested_projects": rec["projects"],
        "secondary_interests": [
            item["domain"] for item in prediction_result["top_3_interests"][1:]
        ],
        "learning_approach": learning_approach,
        "is_physical_domain": is_physical,
        "user_info": user_info
    }


# ===============================================================
# Function: Save Student Response
# ===============================================================
def save_student_response(user_info: dict, user_scores: dict, prediction: dict) -> str:
    """Saves student response and prediction to CSV."""
    _load_ml_libs()
    pd = _pd
    student_data = {
        **user_scores,
        "name": user_info.get("name", "Unknown"),
        "email": user_info.get("email", ""),
        "known_skills": user_info.get("known", ""),
        "want_to_learn": user_info.get("want", ""),
        "goals": user_info.get("goals", ""),
        "predicted_domain": prediction["primary_interest"],
        "confidence": prediction["confidence"],
        "timestamp": _pd.Timestamp.now().isoformat()
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
    """Generates and saves an interest level bar chart."""
    _load_ml_libs()
    np = _np
    plt = _plt
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
    """Runs the command-line interface for the interest assessment."""
    _load_ml_libs()
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
    
    # Save results
    save_student_response(user_info, user_scores, prediction)
    chart_path = generate_interest_chart(user_scores, name)
    
    print(f"\n✅ Results saved!")
    print(f"   Chart: {chart_path}")
    print("\n" + "=" * 60)


# ===============================================================
# Entry Point
# ===============================================================
if __name__ == "__main__":
    run_cli()
