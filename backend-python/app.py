import os
import logging
import importlib
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import get_config
from database import init_db
from routes import auth_bp, profile_bp, admin_bp
from personalized_learning_path import (
    DOMAINS,
    MODEL_PATH,
    DATASET_PATH,
    DATASET_OVERRIDE,
    train_model,
    predict_interest,
    generate_recommendations,
    get_official_learning_curricula,
    save_student_response,
    generate_interest_chart,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _safe_run_seed(module_name: str, function_name: str, success_message: str) -> None:
    """Import and run a seed function safely without startup crashes."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        # Seed files are optional in some environments/repo states.
        # Keep startup clean by logging this at debug level.
        logger.debug("Optional seed module '%s' not found; skipping.", module_name)
        return
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed loading seed module '%s': %s", module_name, exc)
        return

    seed_func = getattr(module, function_name, None)
    if not callable(seed_func):
        logger.debug("Optional seed function '%s.%s' not found; skipping.", module_name, function_name)
        return

    try:
        seed_func()
        logger.info(success_message)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Seed execution failed for '%s.%s': %s", module_name, function_name, exc)

def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Configure CORS
    CORS(app, 
         origins=config.CORS_ORIGINS,
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization', 'X-Admin-Token', 'X-Requested-With'],
         expose_headers=['Content-Disposition', 'X-Admin-Token', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
         max_age=3600)
    
    # Configure rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["1000 per hour"],
        storage_uri="memory://"  # In production, use Redis: redis://localhost:6379
    )
    
    # Enforce HTTPS in production
    @app.before_request
    def enforce_https():
        if config.IS_PRODUCTION and not request.is_secure and request.headers.get('X-Forwarded-Proto', '').lower() != 'https':
            logger.warning(f"Insecure request: {request.remote_addr} {request.method} {request.path}")
            return jsonify({
                'error': 'HTTPS required',
                'detail': 'This server is running in production mode and only accepts HTTPS requests. Use HTTPS, configure your reverse proxy to set X-Forwarded-Proto: https, or set FLASK_ENV=development for local HTTP testing.',
                'error_code': 'HTTPS_REQUIRED',
            }), 403
    
    # Initialize database
    init_db()
    
    # Auto-seed recommendation catalog in development
    if not config.IS_PRODUCTION:
        _safe_run_seed("seed_recommendation_catalog", "seed_recommendation_catalog", "Recommendation catalog auto-seeded for development")
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(profile_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # Dev-only email diagnostics
    if not config.IS_PRODUCTION:
        try:
            from routes.email_debug import bp as email_debug_bp
            app.register_blueprint(email_debug_bp, url_prefix='/api/debug')
        except Exception:
            # Non-fatal: diagnostics are optional
            logger.debug('Email debug blueprint not available')
    
    # Import and register quiz blueprint
    from routes import quiz_bp
    app.register_blueprint(quiz_bp, url_prefix='/api/quiz')

    from routes.messages import messages_bp
    app.register_blueprint(messages_bp, url_prefix='/api/messages')

    from routes.ai_chat import ai_chat_bp
    app.register_blueprint(ai_chat_bp, url_prefix='/api/ai')

    from routes.notes import notes_bp
    app.register_blueprint(notes_bp, url_prefix='/api/notes')
    
    from routes.recommendations import recommendations_bp
    app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')

    from routes.explain import explain_bp
    app.register_blueprint(explain_bp, url_prefix='/api/explain')

    from routes.llm_routes import bp as llm_bp
    app.register_blueprint(llm_bp, url_prefix='/api/llm')

    from routes.interest_intelligence import bp as interest_intelligence_bp
    app.register_blueprint(interest_intelligence_bp, url_prefix='/api/interest')

    # New advanced learning intelligence API (prediction, roadmap, profile, progress)
    from advanced_learning_path.api import bp as learning_intelligence_bp
    app.register_blueprint(learning_intelligence_bp, url_prefix='/api')
    
    from routes.strict_quiz import strict_quiz_bp
    app.register_blueprint(strict_quiz_bp)  # Blueprint has url_prefix='/api/strict-quiz' defined

    # Real-time AI quiz (OpenAI-powered, dynamic, weak-concept retraining)
    from routes.ai_quiz import ai_quiz_bp
    app.register_blueprint(ai_quiz_bp, url_prefix='/api/ai-quiz')

    # Adaptive RL engine (next-action selection, reward updates, policy training)
    from rl.api import bp as rl_bp
    app.register_blueprint(rl_bp, url_prefix='/api/rl')

    # User feedback submission + admin management (Requirement #11)
    from routes.feedback import feedback_bp, admin_feedback_bp
    app.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    app.register_blueprint(admin_feedback_bp, url_prefix='/api/admin/feedback')

    from routes.admin_catalog import admin_catalog_bp
    app.register_blueprint(admin_catalog_bp, url_prefix='/api/admin/catalog')

    # Community routes (interest-based + user-created group chat)
    from routes.community import community_bp
    app.register_blueprint(community_bp, url_prefix='/api/community')

    from routes.remediation import remediation_bp
    app.register_blueprint(remediation_bp, url_prefix='/api/remediation')

    try:
        from models.feedback import Feedback
        Feedback.ensure_indexes()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not ensure feedback indexes: {e}")

    try:
        from models.user_learning_path import UserLearningPath
        UserLearningPath.ensure_indexes()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not ensure user learning path indexes: {e}")

    try:
        from models.remediation_lesson import RemediationLesson
        RemediationLesson.ensure_indexes()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not ensure remediation lesson indexes: {e}")

    # Store limiter on app for cleanup
    app.limiter = limiter
    
    # Register teardown
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        pass  # Database connection is managed globally
    
    return app

# Create app instance
app = create_app()

# Load ML model on startup for performance
MODEL = None
try:
    MODEL = train_model(dataset_path=DATASET_OVERRIDE or DATASET_PATH)
    logger.info("ML model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load ML model: {e}")


@app.route("/", methods=["GET"])
def root():
    """Root probe — use /api/health for full status."""
    return jsonify({
        "service": "PLPG API",
        "status": "ok",
        "health": "/api/health",
        "python_backend": True,
    })


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "model_loaded": MODEL is not None,
        "model_path": MODEL_PATH,
        "dataset": DATASET_OVERRIDE or DATASET_PATH,
        "domains": DOMAINS,
        "version": "1.0.0",
        "python_backend": True
    })


@app.route("/api/interest/curriculum", methods=["GET"])
def api_interest_curriculum():
    """
    Dynamic per-domain topic roadmap and stage projects via OpenAI learning-path API.

    Query params:
      domain — required; canonical name or case-insensitive match (e.g. ``Web Development``).
    """
    domain = (request.args.get("domain") or "").strip()
    if not domain:
        return jsonify({
            "error": "Query parameter 'domain' is required",
            "domains": DOMAINS,
        }), 400

    curricula = get_official_learning_curricula(domain)
    canonical = next((d for d in DOMAINS if d.lower() == domain.lower()), domain)

    return jsonify({
        "requested_domain": domain,
        "canonical_domain": canonical,
        "topic_roadmap": curricula["topic_roadmap"],
        "stage_project_roadmap": curricula["stage_project_roadmap"],
    })


@app.route("/api/interest/train", methods=["POST"])
def api_train():
    """Force retrain (optionally with a specific dataset path)."""
    payload = request.get_json(silent=True) or {}
    dataset_path = payload.get("dataset_path")

    global MODEL
    MODEL = train_model(force_retrain=True, dataset_path=dataset_path)

    return jsonify({
        "message": "Model trained",
        "model_path": MODEL_PATH,
        "dataset": dataset_path or DATASET_OVERRIDE or DATASET_PATH,
        "domains": DOMAINS,
    })


@app.route("/api/interest/predict", methods=["POST"])
def api_predict():
    payload = request.get_json(silent=True) or {}

    user_info = payload.get("user", {})
    scores = payload.get("scores")
    dataset_path = payload.get("dataset_path")
    save_results = payload.get("save_results", True)

    if not isinstance(scores, dict) or not scores:
        return jsonify({"error": "scores must be a non-empty object of domain -> rating"}), 400

    # Validate domain ratings
    sanitized_scores = {}
    for domain in DOMAINS:
        value = scores.get(domain)
        if value is None:
            return jsonify({"error": f"Missing rating for domain: {domain}"}), 400
        try:
            value_int = int(value)
        except (TypeError, ValueError):
            return jsonify({"error": f"Invalid rating for {domain}; must be 1-10"}), 400
        if not 1 <= value_int <= 10:
            return jsonify({"error": f"Rating for {domain} must be between 1 and 10"}), 400
        sanitized_scores[domain] = value_int

    # Use preloaded model unless a retrain is requested
    global MODEL
    if MODEL is None or dataset_path:
        MODEL = train_model(dataset_path=dataset_path)

    prediction = predict_interest(sanitized_scores, model=MODEL, dataset_path=dataset_path)
    recommendations = generate_recommendations(prediction, user_info)

    saved_to = None
    chart_path = None
    if save_results:
        saved_to = save_student_response(user_info, sanitized_scores, prediction)
        chart_path = generate_interest_chart(sanitized_scores, user_info.get("name", "Student"))

    # Save to user profile if authenticated
    from flask import g

    # Try to get authenticated user
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            from models.user import User
            import jwt
            from config import get_config
            config = get_config()
            
            token = auth_header.replace('Bearer ', '')
            decoded = jwt.decode(token, config.JWT_SECRET, algorithms=['HS256'])
            user_id = decoded.get('id')
            
            if user_id:
                # Build comprehensive interest data
                all_interests_list = [
                    {'domain': interest, 'confidence': prob}
                    for interest, prob in prediction.get('all_probabilities', {}).items()
                ]
                
                # Update user's interest assessment
                update_data = {
                    'interestAssessment': {
                        'completed': True,
                        'primaryInterest': prediction['predicted_interest'],
                        'confidence': prediction['confidence'],
                        'modelConfidence': prediction.get('model_confidence', prediction['confidence']),
                        'allInterests': all_interests_list,
                        'completedAt': datetime.utcnow(),
                        'lastUpdated': datetime.utcnow()
                    }
                }
                
                # Also update profile fields for easy access
                update_data['focusDomains'] = [prediction['predicted_interest']]
                
                User.update(user_id, update_data)
                logger.info(f"Saved interest assessment for user {user_id}: {prediction['predicted_interest']} (confidence: {prediction['confidence']:.1%}, model: {prediction.get('model_confidence', 0):.1%})")
        except Exception as e:
            logger.warning(f"Could not save interest assessment to user profile: {e}")

    response = {
        "prediction": prediction,
        "recommendations": recommendations,
        "chart_path": chart_path,
        "saved_to": saved_to,
        "metadata": {
            "domains": DOMAINS,
            "model_path": MODEL_PATH,
            "dataset": dataset_path or DATASET_OVERRIDE or DATASET_PATH,
        },
    }

    return jsonify(response)


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({'success': False, 'message': 'Rate limit exceeded. Please try again later.'}), 429


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("INTEREST_API_PORT", "5000")))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    
    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    # use_reloader=False prevents restart issues with sklearn/scipy on Python 3.13
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
