from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager
from flask_mongoengine import MongoEngine
from pymongo import MongoClient
from hashlib import sha256
import os
from dotenv import load_dotenv, find_dotenv
# from flask_mail import Mail
from .views import views
from .auth import auth

import boto3


#CHARGEMENT DES VARIABLES D'ENVIRONNEMENT
load_dotenv(find_dotenv())


#Récupération des variables d'environnement
MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME")
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD")
MONGODB_URL = os.environ.get("MONGODB_URL")
MONGODB_MODE = os.environ.get("MONGODB_MODE")
SECRET_KEY = os.environ.get("SECRET_KEY")

MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

WASABI_ACCESS_KEY = os.environ.get("WASABI_ACCESS_KEY")
WASABI_SECRET_KEY = os.environ.get("WASABI_SECRET_KEY")
WASABI_REGION = os.environ.get("WASABI_REGION")
WASABI_BUCKET_NAME = os.environ.get("WASABI_BUCKET_NAME")


#CREATION INSTANCES
db = MongoEngine()
# mail = Mail()


def create_app():
    from .models import User
    
    app = Flask(__name__)
    
    #MAIL
    app.config['MAIL_SERVER'] = MAIL_SERVER
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    
    #ROUTES
    app.register_blueprint(views, url_prefix="/")    
    app.register_blueprint(auth, url_prefix="/")
    
    #MONGODB
    app.config['MONGODB_HOST'] = f'mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_URL}/{MONGODB_MODE}'
    app.config['MESSAGE_FLASHING_OPTIONS'] = {'duration': 5}
    app.config['SECRET_KEY'] = SECRET_KEY
    
    #WASABI



    db.init_app(app)
    

    #FLASK-LOGIN
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login' #Page de redirection quand tentative d'accès à une page protégée
    login_manager.init_app(app) #Initialisation du gestionnaire de connexion
    login_manager.login_message = 'Vous devez vous connecter pour accéder à cette page.'
    
    @login_manager.user_loader #Fonction pour charger un utilisateur à partir de son ID. Utilisé par Flask-Login dans le fichier auth.py
    def load_user(user_id):
        user = User.objects(id=user_id).first()
        if user:
            return user
    
    return app