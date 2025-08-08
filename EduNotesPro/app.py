import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
mail = Mail()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///edunotes.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

# Initialize extensions
db.init_app(app)
mail.init_app(app)

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    
    # Create admin user if it doesn't exist
    from models import User, Subject
    from werkzeug.security import generate_password_hash
    
    admin = User.query.filter_by(email='admin@edunotes.com').first()
    if not admin:
        admin_user = User()
        admin_user.username = 'admin'
        admin_user.email = 'admin@edunotes.com'
        admin_user.password_hash = generate_password_hash('admin123')
        admin_user.is_admin = True
        admin_user.security_question = 'What is your favorite color?'
        admin_user.security_answer = 'blue'
        db.session.add(admin_user)
        db.session.commit()
        logging.info("Admin user created: admin@edunotes.com / admin123")
    
    # Create default subjects if they don't exist
    if Subject.query.count() == 0:
        default_subjects = [
            {'name': 'Mathematics', 'code': 'MATH'},
            {'name': 'Physics', 'code': 'PHY'},
            {'name': 'Chemistry', 'code': 'CHEM'},
            {'name': 'Computer Science', 'code': 'CS'},
            {'name': 'Electronics', 'code': 'EC'},
            {'name': 'Mechanical Engineering', 'code': 'MECH'},
            {'name': 'Civil Engineering', 'code': 'CIVIL'},
            {'name': 'English', 'code': 'ENG'},
            {'name': 'Engineering Graphics', 'code': 'EG'},
            {'name': 'Workshop Technology', 'code': 'WT'}
        ]
        
        for subject_data in default_subjects:
            subject = Subject()
            subject.name = subject_data['name']
            subject.code = subject_data['code']
            db.session.add(subject)
        
        db.session.commit()
        logging.info("Default subjects created")

# Import routes after app initialization
import routes
