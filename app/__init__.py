from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
)

def create_app(test_config=None):
    # Templates and static files live in the project root (same layout as the Week 8 sample)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__,
                template_folder=os.path.join(project_root, 'templates'),
                static_folder=os.path.join(project_root, 'static'))

    # Configuration (secrets come from .env, never from code)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///evote.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SEED_PASSWORD'] = os.environ.get('SEED_PASSWORD')
    # JWT tokens for the REST API (same library as the Week 8 sample)
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)  # Week 8 never expired them
    if test_config:
        app.config.update(test_config)
    if not app.config['SECRET_KEY'] or not app.config['JWT_SECRET_KEY']:
        raise RuntimeError('SECRET_KEY or JWT_SECRET_KEY is not set. Run: python scripts/setup_dev.py')

    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # Import models so SQLAlchemy knows about every table
    from app.models import user, elector, election, ballot, audit_log, result  # noqa: F401

    # Register blueprints (one per area of the system)
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.roll import roll_bp
    from app.routes.ballot import ballot_bp
    from app.routes.candidates import candidates_bp
    from app.routes.audit import audit_bp
    from app.routes.results import results_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(roll_bp)
    app.register_blueprint(ballot_bp)
    app.register_blueprint(candidates_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(results_bp)

    # Web security settings: CSRF, cookies, headers (R15-R16)
    from app.utils.security import init_security
    init_security(app)
    from app.utils.auth import init_access_control
    init_access_control(app)   # R05: deny by default

    # Make the logged-in user available in every template (for the menu)
    from app.utils.auth import current_user

    @app.context_processor
    def inject_user():
        return {'current_user': current_user()}

    # Create database tables, and demo data if SEED_PASSWORD is set
    with app.app_context():
        db.create_all()
        from app.utils.audit import protect_audit_log
        protect_audit_log()   # R17: audit_log is append-only
        if app.config['SEED_PASSWORD']:
            from app.utils.seed import seed_if_empty
            seed_if_empty(app.config['SEED_PASSWORD'])

    return app
