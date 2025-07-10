import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from app.database import Base, User

load_dotenv()



login_manager = LoginManager()
login_manager.login_view = 'main.sign_in'

# Define a login manager for the website
@login_manager.user_loader
def load_user(id):
    return db.session.query(User).filter_by(id=id).first()

csrf = CSRFProtect()
db = SQLAlchemy(model_class=Base)

def create_app(create_db=True):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://entirelylukaread:lukareadspass@entirelylukareads.mysql.pythonanywhere-services.com/entirelylukaread$lrdb'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('ELR_DB_URI')
    app.config['SECRET_KEY'] = 'sosec'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True
    }

    login_manager.init_app(app)
    csrf.init_app(app)
    db.init_app(app)


    if create_db:
        with app.app_context():
            db.create_all()

    from app.routes import app as routes
    app.register_blueprint(routes)


    return app

