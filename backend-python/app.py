import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config import get_config
from database import init_db, close_db
from routes import auth_bp, profile_bp, admin_bp
from personalized_learning_path import (
    DOMAINS,
    MODEL_PATH,
    DATASET_PATH,
    DATASET_OVERRIDE,
    train_model,
    predict_interest,
    generate_recommendations,
    save_student_response,
    generate_interest_chart,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
            return jsonify({'error': 'HTTPS required'}), 403
    
    # Initialize database
    init_db()
    
    # Auto-seed quiz templates and admin roles in development
    if not config.IS_PRODUCTION:
        try:
            from seed_quiz_templates import seed_quiz_templates
            seed_quiz_templates()
            logger.info("Quiz templates auto-seeded for development")
        except Exception as e:
            logger.warning(f"Failed to auto-seed quiz templates: {e}")
        
        try:
            from seed_admin_roles import seed_admin_roles
            seed_admin_roles()
            logger.info("Admin roles and permissions auto-seeded for development")
        except Exception as e:
            logger.warning(f"Failed to auto-seed admin roles: {e}")
        
        try:
            from seed_test_users import seed_test_users
            seed_test_users()
            logger.info("Test users auto-seeded for development")
        except Exception as e:
            logger.warning(f"Failed to auto-seed test users: {e}")

        try:
            from seed_notes import seed_notes
            seed_notes()
            logger.info("Notes auto-seeded for development")
        except Exception as e:
            logger.warning(f"Failed to auto-seed notes: {e}")
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(profile_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
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
    from middleware.auth import authenticate_token
    
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
                        'allInterests': all_interests_list,
                        'completedAt': datetime.utcnow(),
                        'lastUpdated': datetime.utcnow()
                    }
                }
                
                # Also update profile fields for easy access
                update_data['focusDomains'] = [prediction['predicted_interest']]
                
                User.update(user_id, update_data)
                logger.info(f"Saved interest assessment for user {user_id}: {prediction['predicted_interest']} ({prediction['confidence']:.1%})")
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
