from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager
from flask_mongoengine import MongoEngine

from pymongo import MongoClient
from hashlib import sha256

import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

#Récupération des variables d'environnement
MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME")
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD")


db = MongoEngine() #Je créé une instance de MongoEngine

def create_app():
    from .models import User
    
    app = Flask(__name__)
    SECRET_KEY = os.environ.get("SECRET_KEY")
    app.config['SECRET_KEY'] = SECRET_KEY
    

    
    
    #Import des routes depuis views.py-----------------------------------------------
    from .views import views
    app.register_blueprint(views, url_prefix="/")
    
    #Import des routes depuis auth.py-----------------------------------------------
    from .auth import auth
    app.register_blueprint(auth, url_prefix="/")
    
    
    app.config['MONGODB_HOST'] = f'mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@cluster0.fyqnwvu.mongodb.net/'
    app.config['MESSAGE_FLASHING_OPTIONS'] = {'duration': 5}
    

    db.init_app(app)
    


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