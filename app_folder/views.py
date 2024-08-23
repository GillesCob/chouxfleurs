from flask import render_template, Blueprint, redirect, url_for, flash, request, session, jsonify
from flask_login import current_user, login_required, logout_user
from .models import Pronostic, User, Project, Product, Participation, Photos, Messages, Tracking_food

from datetime import datetime, timedelta


from bson import ObjectId

from mongoengine.errors import ValidationError

import re

from collections import OrderedDict

# from slugify import slugify
import boto3
from boto3 import s3
import os
from dotenv import load_dotenv, find_dotenv
from botocore.client import Config

from PIL import Image, ExifTags
import io

from collections import defaultdict

#CHARGEMENT DES VARIABLES D'ENVIRONNEMENT
load_dotenv(find_dotenv())
# Configuration Wasabi S3
wasabi_access_key = os.getenv('WASABI_ACCESS_KEY')
wasabi_secret_key = os.getenv('WASABI_SECRET_KEY')
wasabi_region = os.getenv('WASABI_REGION')
wasabi_bucket_name = os.getenv('WASABI_BUCKET_NAME')

# Création d'une session S3
s3_client = boto3.client(
    's3',
    endpoint_url=f'https://s3.{wasabi_region}.wasabisys.com',
    aws_access_key_id=wasabi_access_key,
    aws_secret_access_key=wasabi_secret_key,
    region_name=wasabi_region
)


#Eléments ajoutés
#Eléments pour le scrapping
# import cloudscraper
# import requests

# from requests_html import HTMLSession
# from bs4 import BeautifulSoup



views = Blueprint("views", __name__)

#VARIABLES INITIALES
#Variables concernant le calcul des points pour les pronostics
scores_pronostics = {
    'Sex':{
        'good': 5,
        'bad': 0
    },
    'Name':{
        'good': 20,
        'bad': 0
    },
    'Weight':{
        'good': 10,
        'middle_1': 3,
        'middle_2': 1,
        'bad': 0
    },
    'Height':{
        'good': 10,
        'middle_1': 3,
        'middle_2': 1,
        'bad': 0
    },
    'Date':{
        'good': 10,
        'middle_1': 3,
        'middle_2': 1,
        'bad': 0
    },
    'Total_possible': 0
}

for key, scores in scores_pronostics.items():
    if isinstance(scores, dict) and 'good' in scores:
        scores_pronostics['Total_possible'] += scores['good']

#FONCTIONS -------------------------------------------------------------------------------------------------------------
#Fonction pour récupérer l'info si le user est l'admin du projet en cours ou non
def user_is_admin_project():
    user_id = current_user.id
    current_project_id = session['selected_project']['id'] #J'ai l'id du projet actuellement sauvegardé dans la session
    current_project = Project.objects(id=current_project_id).first() #J'ai l'objet Project actuellement sauvegardé dans la session
    admin_id = current_project.admin.id
    user_is_admin = (user_id == admin_id)
    
    return user_is_admin

# Fonction utilisée pour créer un nouveau pronostic dans la route pronostic
def new_pronostic(user, current_project_id, current_project, pronostics_for_current_project, user_is_admin):
    if request.method == 'POST':
        sex = request.form.get('sex')
        name = request.form.get('name')
        weight = float(request.form.get('weight'))*1000 #Je multiplie par 1000 pour avoir le poids en grammes
        height = float(request.form.get('height'))*10 #Je multiplie par 100 pour avoir la taille en mm
        date = request.form.get('date')
        annee, mois, jour = date.split("-")
        date =  f"{jour}/{mois}/{annee}"
        
        name = capitalize_name(name)
        
        if re.search(r'(-.*-)|(\s.*\s)', name):
            name = "Proposer un nom valide"
                
        new_pronostic = Pronostic(
            user=user,
            sex=sex,
            name=name,
            weight=weight,
            height=height,
            date=date,
            project = current_project_id
        )
        new_pronostic.save()
        
        pronostic_id = new_pronostic.id
        #J'ajoute l'id du nouveau pronostic dans la class User
        current_user.pronostic.append(pronostic_id)
        current_user.save()
        
        #J'ajoute l'id du nouveau pronostic dans la class Project
        current_project.pronostic.append(pronostic_id)
        current_project.save()
        
        pronostic_done = True
        for pronostic in user.pronostic:

            if pronostic in pronostics_for_current_project:
                pronostic_utilisateur = Pronostic.objects(id=pronostic).first()
                prono_sex = pronostic_utilisateur.sex
                prono_name = pronostic_utilisateur.name
                prono_weight = pronostic_utilisateur.weight
                prono_height = pronostic_utilisateur.height
                prono_date = pronostic_utilisateur.date
                
                if user_is_admin:
                   flash("Félicitations pour l'heureux évement !! 🥳 ")    
                else:
                    if name == "Proposer un nom valide":
                        flash('Nom invalide, veuillez mettre à jour votre pronostic', category='error')
                    else:
                        flash('Pronostic sauvegardé avec succès !')
                return {
                    'pronostic_done': pronostic_done,
                    'prono_sex': prono_sex,
                    'prono_name': prono_name,
                    'prono_weight': prono_weight,
                    'prono_height': prono_height,
                    'prono_date': prono_date
                }

#Fonction pour récupérer les réponses aux pronos des users
def get_pronostic_answers():
    current_project_id = session['selected_project']['id']
    current_project_obj = Project.objects(id=current_project_id).first()
    
    pronostics_for_current_project = Pronostic.objects(project=current_project_obj)
    
    pronostic_answers = {}
    for pronostic_obj in pronostics_for_current_project:
        pronostic_user_id = pronostic_obj.user.id
        user_username = User.objects(id=pronostic_user_id).first().username
        
        if pronostic_user_id != current_user.id:
            pronostic_answers[pronostic_user_id] = {
                'username': user_username,
                'sex': pronostic_obj.sex,
                'name': pronostic_obj.name,
                'weight': (pronostic_obj.weight)/1000,
                'height': (pronostic_obj.height)/10,
                'date': pronostic_obj.date,
            }
            
     # Inverser l'ordre du dictionnaire
    pronostic_answers = OrderedDict(reversed(list(pronostic_answers.items())))
    
    return pronostic_answers


#La navbar est évolutive en fonction de l'utilisateur connecté, des projets. Je dois lui envoyer des données et celles-ci doivent être les mêmes pour chaque route. Je crée donc une fonction qui va me permettre de récupérer ces données et de les envoyer dans chaque route. Je n'ai ainsi pas à modifier chaque route à chaque fois que je veux ajouter des éléments à la navbar.
def elements_for_base_template(user_id):
    count_projects = count_user_in_project(user_id)
    projects_dict = create_projects_dict(user_id)
    project_in_session = project_name_in_session()
    has_unread_comments = messages_notifications(user_id)
    hide_page_bool = hide_page()

    
    return {
        'count_projects' : count_projects,
        'projects_dict' : projects_dict,
        'project_name_in_session' : project_in_session,
        'unread_comments' :has_unread_comments,
        'hide_page' : hide_page_bool
            }

#Fonctions appelées par elements_for_base_template()
def count_user_in_project(user_id):
    user_in_project = Project.objects(users__contains=user_id) 
    count_projects = user_in_project.count()
    return count_projects

def create_projects_dict(user_id):
    projects_dict = {}
    user_projects = Project.objects(users=user_id)
    
    for project in user_projects:
        project_id =  str(project.id)
        
        project_admin = project.admin
        project_admin_id = project_admin.id
        project_admin_iban = User.objects(id=project_admin_id).first().iban
        projects_dict[project.name] = {
            "project_id_key": project_id,
            "admin_iban_key": project_admin_iban
        }

    return projects_dict

def project_name_in_session():
    if 'selected_project' in session:
        current_project_name = session['selected_project']['name']
        return current_project_name

def messages_notifications(user_id):
    actual_user = User.objects(id=user_id).first()
    
    if actual_user.notification_enabled == False:
        return False
    else:
        # Récupérer le projet actuellement sélectionné
        selected_project_id = session.get('selected_project', {}).get('id')
        if selected_project_id:
            project = Project.objects(id=selected_project_id).first()
        else:
            project = None
            
        # Initialiser le flag pour les commentaires non lus
        has_unread_comments = False
        
        if project:
            photos = Photos.objects(project=project)
            for photo in photos:
                # Récupérer tous les commentaires pour chaque photo
                comments = Messages.objects(photo=photo)
                # Vérifier si au moins un commentaire n'a pas été vu par l'utilisateur
                if any(actual_user not in comment.seen_by_users for comment in comments):
                    has_unread_comments = True
                    break  # Pas besoin de continuer si on a trouvé au moins un commentaire non lu
        return has_unread_comments

#Fonction afin d'ajouter un projet à la session
def project_in_session(user_id, elements_for_base):
    
    if 'selected_project' not in session:
        user_in_project = Project.objects(users__contains=user_id) #user_id dans la liste users d'un projet ?
        
        if user_in_project:
            first_project = user_in_project.first() 
            
            session['selected_project'] = { #Création de la session
                'id': str(first_project.id),
                'name': first_project.name
            }
            
        else:
            flash("Veuillez créer ou rejoindre un projet avant d'accéder à une liste de naissance", category='error')
            return redirect(url_for('views.my_projects', **elements_for_base))
            

#Fonction pour récupérer SA participation aux projets
def user_participations_side_project_func():
    user_participations_side_project = {}
    
    #J'ai dans ma class user la liste des participations
    user_participations_list = current_user.participation #Je récupère les objets Participation pour le user actuel
    
    if user_participations_list:
        for participation in user_participations_list:
            participation_id = ObjectId(participation) #Je récupère l'id de la participation
            participation_obj = Participation.objects(id=participation_id).first() #Je récupère l'objet Participation
            #Je récupère l'id du produit pour lequel la participation a été faite
            product_id = participation_obj.product.id
            
            #Je récupère l'id du projet pour lequel la participation a été faite
            project_id = participation_obj.project.id
            
            project_name = Project.objects(id=project_id).first().name #Je récupère le nom du projet
            
            product_name = Product.objects(id=product_id).first().name #Je récupère le nom du produit
            
            
            if participation_obj.type == "€":
                participation_amount = participation_obj.amount #Je récupère le montant de la participation
                participation_amount = f"{participation_amount}€"
            elif participation_obj.type  == "donation":
                participation_amount = "Don"
            else:
                participation_amount = "Prêt"

            
            status = participation_obj.status
            
            #Je vérifie que la participation n'a pas été faite pour le compte de quelqu'un d'autre sur son propre projet
            if participation_obj.other_user == None:
                if project_name not in user_participations_side_project:
                    user_participations_side_project[project_name] = []  # Créez une liste vide pour chaque nouvel utilisateur
            
                user_participations_side_project[project_name].append((participation_id, product_name, participation_amount, status))
    else:
        user_participations_side_project = None
            
    return user_participations_side_project

#Fonction pour récupérer LES participations à SON projet
def my_project_participations():

    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    admin_project = Project.objects(admin=user_id).first()
    
    user_participations = {}
    
    try:
        project_products= admin_project.product #Je récupère les produits du projet pour lequel mon user est l'admin
    except (KeyError, AttributeError):
        flash("Pas de produit, je suis bloqué", category='error')
        return redirect(url_for('views.home_page', user=current_user, **elements_for_base))
    
    
    for project_product in project_products:
        product_id = ObjectId(project_product)
        product_participations = Participation.objects(product=product_id)
        
        for product_participation in product_participations:
            participation_id = product_participation.id
            user = product_participation.user
            user_id = ObjectId(user.id)
            
            product_name = Product.objects(id=product_id).first().name
            participant_id = product_participation.user.id
            participant_username = User.objects(id=participant_id).first().username
            
            if product_participation.other_user != None:
                participant_username = product_participation.other_user
            
            if product_participation.type == "€":
                amount = product_participation.amount
                amount = f"{amount}€"
            elif product_participation.type == "donation":
                amount = "Don"
            else:
                amount = "Prêt"
            date = product_participation.participation_date
            date = date.strftime('%d-%m-%Y')
            status = product_participation.status

            # Ajoutez la participation au dictionnaire user_participations
            if participant_username not in user_participations:
                user_participations[participant_username] = []  # Créez une liste vide pour chaque nouvel utilisateur
            
            user_participations[participant_username].append((participation_id, participant_username, product_name, amount, date, status))
            
    return user_participations

#Fonction afin de récupérer le choix du sexe fait par l'utilisateur afin de personnaliser les boutons des interfaces
def get_gender_choice(current_project):
    gender_choice = "no_gender"
        
    #Je récupe le choix du user concernant le sexe afin de personnaliser les boutons
    #Je dois cependant gérer le cas ou je n'ai pas encore de pronostic pour le projet actuellement sauvegardé dans la session
    try :
        actual_project_pronostics_base_list = current_project.pronostic #Je récupère la liste des pronostics pour le projet actuellement sauvegardé dans la session
        actual_project_pronostics_list = list(actual_project_pronostics_base_list)
        
        user_pronostics_base_list = current_user.pronostic #Je récupère la liste des pronostics pour le user actuellement connecté
        user_pronostics_list = list(user_pronostics_base_list)
        
        for project_id in actual_project_pronostics_list:
            if project_id in user_pronostics_list:
                pronostic_utilisateur = Pronostic.objects(id=project_id).first()
                gender_choice = pronostic_utilisateur.sex
                
                
    except:
        pass
    
    return gender_choice

#Fonction permettant d'avoir les noms, même composés, avec les premies lettres en majuscule
def capitalize_name(name):
    # Diviser le prénom par les tirets et les espaces
    parts = name.replace('-', ' - ').split()
    # Capitaliser chaque partie du prénom
    capitalized_parts = [part.capitalize() for part in parts]
    # Réassembler les parties avec les tirets et les espaces
    result = ' '.join(capitalized_parts).replace(' - ', '-')
    return result

#Fonction afin de récupérer les résultats du prono de l'admin
def get_admin_pronostic_answers():
    current_project_id = session['selected_project']['id']
    current_project_obj = Project.objects(id=current_project_id).first()
    pronostics_for_current_project = current_project_obj.pronostic
    
    project_admin_obj = current_project_obj.admin
    project_admin_id = project_admin_obj.id
    
    admin_results = {}
    for pronostic_id in pronostics_for_current_project:
        pronostic_obj = Pronostic.objects(id=pronostic_id).first()

        if pronostic_obj.user.id == project_admin_id :
            admin_results['prono_sex'] = pronostic_obj.sex
            admin_results['prono_name'] = pronostic_obj.name
            admin_results['prono_weight'] = pronostic_obj.weight/1000
            admin_results['prono_height'] = pronostic_obj.height/10
            admin_results['prono_date'] = pronostic_obj.date
            
    return admin_results

#Fonction pour formater le temps
def format_time(timedelta_obj):
    if not isinstance(timedelta_obj, timedelta):
        return ''
    total_seconds = int(timedelta_obj.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def hide_page():
    ok_gilles = False
    mails_ok = ["gilles@gilles.com", "bielmann.maxime@gmail.com"]
    if current_user.email in mails_ok:
        ok_gilles = True
    return ok_gilles

#ROUTES -------------------------------------------------------------------------------------------------------------
@views.route('/')
@views.route('/home_page',methods=['GET', 'POST'])
def home_page():
    user_identified_bool = False
    user_in_project_bool = False
    user_is_admin_project_bool = False
    user_did_pronostic_bool = False
    user_did_participation_bool = False
    affiliation_link_used_bool = False
    
    if current_user.is_authenticated:
        user_identified_bool = True
        
        user_id = current_user.id
        user = User.objects(id=user_id).first()
        
        user_in_project = Project.objects(users__contains=user_id)
        if user_in_project: #le user est dans au moins un projet
            user_in_project_bool = True
            user_is_admin_project = Project.objects(admin=user_id).first()
            
            if user_is_admin_project:
                user_is_admin_project_bool = True
                user_project_has_users = len(user_is_admin_project.users)
                if user_project_has_users > 1:
                    affiliation_link_used_bool = True

            
        user_did_pronostic_bool = bool(user.pronostic)
        user_did_participation_bool = bool(user.participation)
        user_informations = {
            'user_identified': user_identified_bool,
            'user_in_project': user_in_project_bool,
            'user_is_admin_project': user_is_admin_project_bool,
            'user_did_pronostic': user_did_pronostic_bool,
            'user_did_participation': user_did_participation_bool,
            'affiliation_link_used': affiliation_link_used_bool
        }

        elements_for_base = elements_for_base_template(user_id)
        
        if 'selected_project' not in session:
             #user_id dans la liste users d'un projet ?
            
            if user_is_admin_project_bool :
                session['selected_project'] = { #Création de la session
                    'id': str(user_is_admin_project.id),
                    'name': user_is_admin_project.name
                }
            
            elif user_in_project_bool:
                first_project = user_in_project.first() 
                session['selected_project'] = { #Création de la session
                    'id': str(first_project.id),
                    'name': first_project.name
                }
            
            else:
                return render_template('Home page/home.html', user_informations=user_informations, **elements_for_base)
                
            return redirect(url_for('views.home_page'))
        
        return render_template('Home page/home.html', user_informations=user_informations, **elements_for_base)
    
    user_informations = {
        'user_identified': user_identified_bool,
    }
    return render_template('Home page/home.html', user_informations=user_informations, count_projects=0)

#ROUTES "LISTE NAISSANCE" -------------------------------------------------------------------------------------------------------------
@views.route('/liste_naissance')
@login_required
def liste_naissance():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    current_user_18 = current_user.over_18
    if current_user_18 == False:
        flash("Vous devez être majeur pour accéder à cette page", category='error')
        return redirect(url_for('views.home_page', **elements_for_base))
    
    #Variables initiales
    total_money_needed = 0
    total_money_participations = 0

    
    try: 
        current_project_id = session['selected_project']['id']
        current_project = Project.objects(id=current_project_id).first()
        
        gender_choice = get_gender_choice(current_project)
        session['gender_choice'] = gender_choice
        
        user_id = current_user.id
        admin_id = current_project.admin.id
        user_is_admin = (user_id == admin_id)
        session['admin_id'] = admin_id
        session['user_is_admin'] = user_is_admin
        
        products_for_current_project = current_project.product
        
        if products_for_current_project:
            
            products = []
            

            for product_id in products_for_current_project:
                product = Product.objects(id=product_id).first()
                products.append({
                    'name': product.name,
                    'description': product.description,
                    'image_url': product.image_url,
                    'price': product.price,
                    'url_source': product.url_source,
                    'already_paid':product.already_paid,
                    'id': product.id,
                    'left_to_pay': product.price-product.already_paid
                })
                
                if product.type == "€" :
                    total_money_needed += product.price
                    
                    product_participations = product.participation
                    for product_participation in product_participations:
                        participation = Participation.objects(id=product_participation).first()
                        participation_status = participation.status
                        if participation_status == "Terminé" or participation_status == "Reçu":
                            total_money_participations += participation.amount

            # -----------------
            products = sorted(products, key=lambda x: x['left_to_pay'], reverse=True)
            
            # -----------------
            if user_is_admin :
                return render_template('Products/liste_naissance.html', **elements_for_base, total_money_needed=total_money_needed, total_money_participations=total_money_participations, products=products)
            else:
                return render_template('Products/liste_naissance.html', **elements_for_base, total_money_needed=total_money_needed, total_money_participations=total_money_participations, products=products)
            
        else:
            return render_template('Products/liste_naissance.html', user_is_admin=user_is_admin, total_money_needed=total_money_needed, total_money_participations=total_money_participations, **elements_for_base)
    
    except (KeyError, AttributeError):
        flash("Veuillez créer ou rejoindre un projet avant d'accéder à une liste de naissance", category='error')
        return redirect(url_for('views.my_projects', **elements_for_base))
    
@views.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    
    #Ajout d'un nouveau produit
    if request.method == 'POST':
       
        current_project_id = session['selected_project']['id']
        name = request.form.get('product_name')
        description = request.form.get('product_description')
        price = request.form.get('product_price')
        already_paid = 0
        url_source = request.form.get('product_url_source')     
        
        
        # image_url = img_url
        image_url = request.form.get('product_image_url')
        type = "€"
        
        # Création du nouveau produit avec envoi des infos précedemment collectées
        new_product = Product(project=current_project_id, name=name, description=description, image_url=image_url, price=price, url_source=url_source, already_paid=already_paid, type=type)
        new_product.save()
        
        # J'ajoute l'id du nouveau produit dans la liste des produits de mon objet Project
        current_project = Project.objects(id=current_project_id).first()
        new_product_id = new_product.id
        
        current_project.product.append(new_product_id)
        current_project.save()
        
        flash(f'Produit créé avec succès !', category='success')
        
        return redirect(url_for('views.liste_naissance'))
                
    return render_template('Products/add_product.html',  **elements_for_base)

@views.route('/update_product/<product_id>', methods=['GET', 'POST'])
@login_required
def update_product(product_id):
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    product = Product.objects(id=product_id).first()

    if request.method == 'POST':
        name = request.form.get('product_name')
        description = request.form.get('product_description')
        image_url = request.form.get('product_image_url')
        price = request.form.get('product_price')
        left_to_pay = request.form.get('product_left_to_pay')
        url_source = request.form.get('product_url_source')
        
        if name:
            product.name = name
        product.description = description
        if price:
            product.price = price
        if left_to_pay:
            if left_to_pay > product.price:
                left_to_pay = product.price
                already_paid = int(product.price) - int(left_to_pay)
                product.already_paid = already_paid
            else:
                already_paid = int(product.price) - int(left_to_pay)
                product.already_paid = already_paid
        if url_source:
            product.url_source = url_source
        if image_url:
            product.image_url = image_url
        
        product.save()
        
        flash('Produit mis à jour avec succès !')
        return redirect(url_for('views.product_details', product_id=product_id))
    
    return render_template('Products/update_product.html', user=current_user, **elements_for_base, product=product)
  
@views.route('/product_details/<product_id>', methods=['GET','POST'])
@login_required
def product_details(product_id):
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    product = Product.objects(id=product_id).first()
    
    left_to_pay = product.price-product.already_paid
    
    participation_choice = "no_choice"
    
    if product:
        if request.method=='POST':
            if 'participation' in request.form:
                participation_choice = "payment"
                
            elif 'donation' in request.form:
                participation_choice = "donation"
            
            elif 'lending' in request.form:
                participation_choice = "lending"
        
        return render_template('Products/product_details.html', product=product, **elements_for_base, left_to_pay=left_to_pay, participation_choice=participation_choice)
    else:
        # Si le produit n'est pas trouvé, renvoyer une erreur 404 ou rediriger vers une autre page
        return render_template('Products/liste_naissance.html', **elements_for_base), 404

@views.route('/confirm_participation_loading/<product_id>', methods=['GET','POST'])
@login_required
def confirm_participation_loading(product_id):
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    if request.method == 'POST':
        user = User.objects(id=user_id).first()
        project = session.get('selected_project', {}).get('id')
        
        type_of_participation = request.form.get('submit_btn')
        if type_of_participation == "€":
            type = "€"
            participation = request.form.get('price_input')
            status = "Promesse"
        elif type_of_participation == "donation":
            type = "donation"
            participation = 0
            status = "Promesse"
        else:
            type = "lending"
            participation = 0
            status = "Promesse"
            
        other_user_participation = request.form.get('other_user')
        
        if other_user_participation:
            new_participation = Participation(user=user_id, type=type, project=project, product=product_id, amount=participation, participation_date=datetime.now(), status=status, other_user=other_user_participation)
        
        else:
            new_participation = Participation(user=user_id, type=type, project=project, product=product_id, amount=participation, participation_date=datetime.now(), status=status)
            
        new_participation.save()
        
        product = Product.objects(id=product_id).first()
        
        if type == "€":
            product.already_paid += int(participation)
            product.participation.append(new_participation.id)
            product.type = "€"
        else:
            previous_participation = product.already_paid
            value_donation = product.price - previous_participation
            product.already_paid += value_donation
            product.participation.append(new_participation.id)
            
        if type == "donation":
            product.type = "donation"
        elif type == "lending":
            product.type = "lending"
            
            
        product.save()
        
        user.participation.append(new_participation.id)
        user.save()

                
        return render_template('Products/confirm_participation_loading.html', product=product, **elements_for_base, participation=participation)
    
    if product:
        return render_template('Products/product_participation.html', product=product, **elements_for_base)
    else:
        return render_template('Products/liste_naissance.html', **elements_for_base), 404

@views.route('/confirm_participation/<participation>', methods=['GET','POST'])
@login_required
def confirm_participation(participation):
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    #Récupération du iban de l'admin du projet
    admin_id = session['admin_id']
    admin_iban = User.objects(id=admin_id).first().iban
    
    #Récupération du nom du user
    username = current_user.username

    return render_template('Products/confirm_participation.html', **elements_for_base, admin_iban=admin_iban, participation=participation, username=username)

@views.route('/delete_product/<product_id>', methods=['GET','POST'])
@login_required
def delete_product(product_id):
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    # Je récupère l'objet Product concerné
    product = Product.objects(id=product_id).first()
    # Je récupère la liste des participations pour ce produit
    participation_list = product.participation

    #Je supprime tous les objets Participation dont l'id est dans la liste participation_list de mon objet Product
    for participation_id in participation_list:
        Participation.objects(id=participation_id).delete()

    # Suppression du produit dans le projet
    project_id = session['selected_project']['id']
    project = Project.objects(id=project_id).first()
    
    #Je récupère la liste des produits du projet
    products_in_project = project.product
    
    for product_in_project in products_in_project:
        #Je transforme products_in_project en str pour pouvoir comparer
        product_in_project_str = str(product_in_project)

        if product_in_project_str == product_id:
            project.update(pull__product=product_in_project)
            project.save()
                
    product.delete()
    
    flash('Produit supprimé avec succès !', category='success')

    return redirect(url_for('views.liste_naissance'))


#ROUTES "PRONOS" -------------------------------------------------------------------------------------------------------------
@views.route('/pronostic', methods=['GET', 'POST'])
@login_required
def pronostic():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    at_least_one_pronostic = False
    # Si le user est déjà dans un projet et que je n'ai rien dans la session (parce que je viens de me connecter), je récupère le premier projet dans lequel le user est afin d'ouvrir une session et ne pas avoir à choisir un projet à chaque fois que je me connecte.
    #Si une session est déjà ouverte, je skip cette étape
    if 'selected_project' not in session:
        user_in_project = Project.objects(users__contains=user_id)
        if user_in_project:
            first_project = user_in_project.first() 
            first_project_id = first_project.id
            
            # Ajouter les données du premier projet trouvé dans la session
            session['selected_project'] = {
                'id': str(first_project_id),
                'name': first_project.name
            }
    try:
        current_project_id = session['selected_project']['id'] #J'ai l'id du projet actuellement sauvegardé dans la session
        current_project = Project.objects(id=current_project_id).first() #J'ai l'objet Project actuellement sauvegardé dans la session
        end_pronostics = current_project.end_pronostics
        admin_id = current_project.admin.id
        
        try:
            due_date = current_project.due_date
            due_date = due_date.strftime('%d/%m/%Y')

        except Exception as e:
            due_date = None
            
        try:
            clue_name = current_project.clue_name

        except Exception as e:
            clue_name = None
            
        user_is_admin = (user_id == admin_id)
        
        pronostics_for_current_project = current_project.pronostic #J'ai la liste des pronostics pour le projet actuellement sauvegardé dans la session

        if pronostics_for_current_project : #J'ai au moins 1 pronostic pour le projet sélectionné
            at_least_one_pronostic = True
            if current_user.pronostic : #Si le user actuel a déjà un pronostic, peut-importe sur quel projet

                current_user_pronostic_bool = bool(set(pronostics_for_current_project) & set(current_user.pronostic))
                
                if current_user_pronostic_bool == True : #Le user a déjà fait son prono pour le projet actuel
                    current_user_pronostic = (set(pronostics_for_current_project) & set(current_user.pronostic)).pop()
                    pronostic_utilisateur = Pronostic.objects(id=current_user_pronostic).first() #J'ai l'objet Pronostic actuellement sauvegardé dans la session
                    
                    prono_sex = pronostic_utilisateur.sex
                    prono_name = pronostic_utilisateur.name
                    prono_weight = float(pronostic_utilisateur.weight) /1000 #Je divise par 1000 pour avoir le poids en kg
                    prono_height = float(pronostic_utilisateur.height)/10 #Je divise par 10 pour avoir la taille en cm
                    prono_date = pronostic_utilisateur.date
                    
                    pronostic_done=True
                    
                    prono_sex_btn = prono_sex
                    
                    #Petite astuce ici permettant d'afficher les infos du gagnant en 1er en arrivant sur pronostic
                    go_to_pronostic = False

                    if end_pronostics == True :
                        admin_results = get_admin_pronostic_answers()
                        prono_sex_btn = admin_results['prono_sex']
                        
                        if request.method == 'POST':
                            go_to_pronostic = request.form.get('go_to_pronostic')
                            
                        if go_to_pronostic == False :
                            return redirect(url_for('views.pronostic_winner', **elements_for_base))
                        
                        else:
                            score_prono_user = {
                                'Sex' : pronostic_utilisateur.sex_score,
                                'Name' : pronostic_utilisateur.name_score,
                                'Weight' : pronostic_utilisateur.weight_score,
                                'Height' : pronostic_utilisateur.height_score,
                                'Date' : pronostic_utilisateur.date_score,
                                'Total' : pronostic_utilisateur.total_score
                            }
                            
                            total_possible = (scores_pronostics['Total_possible'])
                            
                            return render_template('Pronostics/pronostic.html', user=current_user, user_is_admin=user_is_admin, pronostic_done=pronostic_done, prono_sex=prono_sex, prono_name=prono_name, prono_weight=prono_weight, prono_height=prono_height, prono_date=prono_date, at_least_one_pronostic=at_least_one_pronostic, end_pronostics=end_pronostics, go_to_pronostic=go_to_pronostic, score_prono_user=score_prono_user, scores_pronostics=scores_pronostics, total_possible=total_possible, prono_sex_btn=prono_sex_btn, **elements_for_base)
                    
                    else:
                        return render_template('Pronostics/pronostic.html', user=current_user, user_is_admin=user_is_admin, pronostic_done=pronostic_done, prono_sex=prono_sex, prono_name=prono_name, prono_weight=prono_weight, prono_height=prono_height, prono_date=prono_date, at_least_one_pronostic=at_least_one_pronostic, end_pronostics=end_pronostics, go_to_pronostic=go_to_pronostic, prono_sex_btn=prono_sex_btn, **elements_for_base)

                else : #
                    result = new_pronostic(current_user, current_project_id, current_project, pronostics_for_current_project, user_is_admin)
                    if result:
                        if user_is_admin :
                            current_project.end_pronostics = True
                            end_pronostics = current_project.end_pronostics
                            current_project.save()
                            
                        return redirect(url_for('views.pronostic'))
            
            else : #J'arrive ici si le user n'a JAMAIS fait de pronostic sur aucun projet ET n'est pas le 1er à pronostiquer pour le projet en cours
                try:
                    result = new_pronostic(current_user, current_project_id, current_project, pronostics_for_current_project, user_is_admin)
                except:
                    return redirect(url_for('views.pronostic'))
                if result:
                    if user_is_admin :
                        current_project.end_pronostics = True
                        end_pronostics = current_project.end_pronostics
                        current_project.save()
                    return redirect(url_for('views.pronostic'))

        else : #C'est ici que va s'enregistrer le 1er prono de mon projet
            result = new_pronostic(current_user, current_project_id, current_project, pronostics_for_current_project, user_is_admin)
            
            if result:
                if user_is_admin :
                    current_project.end_pronostics = True
                    end_pronostics = current_project.end_pronostics
                    current_project.save()

                return redirect(url_for('views.pronostic'))
            
    except (KeyError, AttributeError):
        flash("Veuillez créer ou rejoindre un projet avant d'accéder aux pronostics", category='error')
        return redirect(url_for('views.my_projects', user=current_user, **elements_for_base))
    
    #J'arrive ici si je n'ai pas encore fait mon prono pour le projet actuel
    return render_template('Pronostics/pronostic.html', user_is_admin=user_is_admin, at_least_one_pronostic=at_least_one_pronostic, end_pronostics=end_pronostics, due_date=due_date, clue_name=clue_name, **elements_for_base)

@views.route('/update_pronostic', methods=['GET', 'POST']) 
@login_required
def update_pronostic():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    user = current_user
    
    current_project_id = session['selected_project']['id'] #J'ai l'id du projet actuellement sauvegardé dans la session
    current_project = Project.objects(id=current_project_id).first() #J'ai l'objet Project actuellement sauvegardé dans la session     
        
    try:
        due_date = current_project.due_date
        due_date = due_date.strftime('%d/%m/%Y')

    except Exception as e:
        due_date = None
        
    try:
        clue_name = current_project.clue_name

    except Exception as e:
        clue_name = None
        

    current_project_id = session['selected_project']['id'] #J'ai l'id du projet actuellement sauvegardé dans la session
    current_project = Project.objects(id=current_project_id).first() #J'ai l'objet Project actuellement sauvegardé dans la session
    pronostics_for_current_project = current_project.pronostic #J'ai la liste des pronostics pour le projet actuellement sauvegardé dans la session
    
    for pronostic in user.pronostic:
        if pronostic in pronostics_for_current_project:
            pronostic_utilisateur = Pronostic.objects(id=pronostic).first()
    
            prono_sex = pronostic_utilisateur.sex
            prono_name = pronostic_utilisateur.name
            prono_weight = pronostic_utilisateur.weight/1000
            prono_height = pronostic_utilisateur.height/10
            prono_date = pronostic_utilisateur.date
            
                        
            if request.method == 'POST':
                sex = request.form.get('sex')
                name = request.form.get('name')
                weight = float(request.form.get('weight'))*1000
                height = float(request.form.get('height'))*10
                date = request.form.get('date')
                if date:
                    annee, mois, jour = date.split("-")
                    date =  f"{jour}/{mois}/{annee}"
                    
                if re.search(r'(-.*-)|(\s.*\s)', name):
                    flash('Nom invalide', category='error')
                    return redirect(url_for('views.update_pronostic'))
                
                if sex:
                    pronostic_utilisateur.sex = sex
                if name:
                    pronostic_utilisateur.name = name
                if weight:
                    pronostic_utilisateur.weight = weight
                if height: 
                    pronostic_utilisateur.height = height
                if date:
                    pronostic_utilisateur.date = date
                    
                # Enregistrer les modifications
                pronostic_utilisateur.save()
                
                pronostic_done = True
                prono_sex = pronostic_utilisateur.sex
                prono_name = pronostic_utilisateur.name
                prono_weight = (pronostic_utilisateur.weight)/1000
                prono_height = (pronostic_utilisateur.height)/10
                prono_date = pronostic_utilisateur.date
                
                
                flash('Pronostic mis à jour avec succès !')
                return redirect(url_for('views.pronostic'))
    
    return render_template('Pronostics/update_pronostic.html', user=current_user, prono_sex=prono_sex, prono_name=prono_name, prono_weight=prono_weight, prono_height=prono_height, prono_date=prono_date, due_date=due_date, clue_name=clue_name, **elements_for_base)

@views.route('/all_pronostics', methods=['GET', 'POST'])
@login_required
def all_pronostics():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    current_project_id = session['selected_project']['id']
    current_project = Project.objects(id=current_project_id).first()

    end_pronostics = current_project.end_pronostics
    
    pronostic_ids = current_project.pronostic  # Cette liste contient les IDs des pronostics
    pronostics = Pronostic.objects(id__in=pronostic_ids)
    
    user_id = current_user.id
    
    user_is_admin = user_is_admin_project()
    
    #Je récupère le choix du sexe fait par le user afin de personnaliser les boutons des interfaces
    gender_choice = get_gender_choice(current_project)
    
    
    number_of_pronostics = len(pronostics)
    sex_girl = 0
    weight_values = []
    height_values = []
    timestamps = []
    names = {}
    
    
    for pronostic in pronostics:
         
        weight_value = (pronostic.weight)
        weight_values.append(weight_value)
        
        height_value = (pronostic.height)
        height_values.append(height_value)
        
        if pronostic.sex == "Fille":
            sex_girl +=1
            
        date_obj = (datetime.strptime(pronostic.date, "%d/%m/%Y"))
        timestamp = date_obj.timestamp()
        timestamps.append(timestamp)
        
        name = pronostic["name"]
        if name in names:
            names[name] += 1
        else:
            names[name] = 1

    #Poids moyen
    average_weight = sum(weight_values) / len(weight_values)
    average_weight = (round(average_weight/1000, 2)) #Je divise par 1000 pour avoir le poids en kg

    #Taille moyenne
    average_height = sum(height_values) / len(height_values)
    average_height = (round(average_height/10, 1)) #Je divise par 100 pour avoir la taille en cm
    
    #Date moyenne
    average_timestamp = sum(timestamps) / len(timestamps)
    average_date = datetime.fromtimestamp(average_timestamp)
    average_date = average_date.strftime('%d/%m/%Y')

    #Pourcentage de filles/gars
    percentage_girl = int(round((sex_girl*100)/number_of_pronostics,0))
    percentage_boy = int(round(100 - percentage_girl,0))
    
    #Tris des prénoms avec ceux proposés plusieurs fois en premier
    names = dict(sorted(names.items(), key=lambda item: item[1], reverse=True))

    
    return render_template('Pronostics/all_pronostics.html', user_is_admin=user_is_admin, average_weight=average_weight, average_height=average_height, average_date=average_date, percentage_girl=percentage_girl, percentage_boy=percentage_boy, names=names, number_of_pronostics=number_of_pronostics, end_pronostics=end_pronostics, **elements_for_base, gender_choice=gender_choice)

@views.route('/pronostic_winner', methods=['GET', 'POST'])
@login_required
def pronostic_winner():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    #Récupération des éléments afin de pouvoir récupérer les infos
    current_project_id = session['selected_project']['id']
    current_project = Project.objects(id=current_project_id).first()
    pronostics_for_current_project = current_project.pronostic
    
    #Je mets ici toute la mécanique de calcul des points afin de déterminer le gagnant
    project_admin = current_project.admin
    project_admin_id = project_admin.id
    
    admin_results = get_admin_pronostic_answers()
    prono_sex_btn = admin_results['prono_sex']
    
    admin_id = current_project.admin.id
    user_is_admin = (user_id == admin_id)
       
    #Je récupere ensuite les infos des users
    number_of_winners = 0
    
    for pronostic_id in pronostics_for_current_project:                                        
        pronostic_user = Pronostic.objects(id=pronostic_id).first()
        
        if pronostic_user.user.id != project_admin_id :
            user_prono_sex = pronostic_user.sex
            user_prono_name = pronostic_user.name
            user_prono_weight = pronostic_user.weight
            user_prono_height = pronostic_user.height
            user_prono_date = pronostic_user.date

            
            #Je fais le comparatif entre les pronostics de l'admin et ceux des users
            
            #Comparatif pour le sexe
            if user_prono_sex == admin_results['prono_sex']:
                sex_score = scores_pronostics['Sex']['good']
            else:
                sex_score = scores_pronostics['Sex']['bad']
             
            #Comparatif pour le nom   
            if user_prono_name == admin_results['prono_name']:
                name_score = scores_pronostics['Name']['good']
            else:
                name_score = scores_pronostics['Name']['bad']
            
            #Comparatif pour le poids   
            user_prono_weight = float(user_prono_weight)
            admin_results['prono_weight'] = float(admin_results['prono_weight'])
            
            # Définition des tolérances pour les comparaisons de poids
            tolerance_middle_1 = 11
            tolerance_middle_2 = 51
            ecart_abs_weight = abs(user_prono_weight - admin_results['prono_weight'])

            # Comparer les poids avec les différentes tolérances
            if ecart_abs_weight == 0:
                weight_score = scores_pronostics['Weight']['good']
            elif ecart_abs_weight < tolerance_middle_1:
                weight_score = scores_pronostics['Weight']['middle_1']
            elif ecart_abs_weight <= tolerance_middle_2:
                weight_score = scores_pronostics['Weight']['middle_2']
            else:
                weight_score = scores_pronostics['Weight']['bad']
                
                
            # Définition des tolérances pour les comparaisons de taille
            tolerance_middle_1 = 1
            tolerance_middle_2 = 5
            ecart_abs_height = abs((user_prono_height) - (admin_results['prono_height']))
            
            #Comparatif pour la taille
            user_prono_height = float(user_prono_height)
            admin_results['prono_height'] = float(admin_results['prono_height'])
            
            if ecart_abs_height == 0:
                height_score = scores_pronostics['Height']['good']
            elif ecart_abs_height <= tolerance_middle_1:
                height_score = scores_pronostics['Height']['middle_1']
            elif ecart_abs_height <= tolerance_middle_2:
                height_score = scores_pronostics['Height']['middle_2']
            else:
                height_score = scores_pronostics['Height']['bad']
            
            #Comparatif pour la date
            
            tolerance_middle_1 = 1#jour
            tolerance_middle_2 = 2#jours
            
            user_prono_date = datetime.strptime(user_prono_date, '%d/%m/%Y')
            admin_result_date = datetime.strptime(admin_results['prono_date'], '%d/%m/%Y')
            
            difference_days = abs((user_prono_date - admin_result_date).days)
            
            if difference_days == 0 :
                date_score = scores_pronostics['Date']['good']
            elif difference_days == tolerance_middle_1:
                date_score = scores_pronostics['Date']['middle_1']
            elif difference_days <= tolerance_middle_2:
                date_score = scores_pronostics['Date']['middle_2']
            else:
                date_score = scores_pronostics['Date']['bad']
            
            
            pronostic_user.sex_score = sex_score
            pronostic_user.name_score = name_score
            pronostic_user.weight_score = weight_score
            pronostic_user.height_score = height_score
            pronostic_user.date_score = date_score
            pronostic_user.total_score = sex_score + name_score + weight_score + height_score + date_score
            pronostic_user.save()
    
    
    max_total_score = float('-inf')  # Initialisation à un nombre très bas
    pronostics_with_max_score = []
    for pronostic_id in pronostics_for_current_project:
        pronostic = Pronostic.objects(id=pronostic_id).first()
        
        if pronostic.user.id != project_admin_id :            
            total_score = pronostic.total_score
            if total_score > max_total_score:
                max_total_score=total_score
                pronostics_with_max_score = [pronostic]
            elif total_score == max_total_score:
                pronostics_with_max_score.append(pronostic)
    
    high_score_pronostics = []          
    for high_pronostic in pronostics_with_max_score:
        high_score_pronostic = {
            'username' : high_pronostic.user.username,
            'sex' : high_pronostic.sex,
            'name' : high_pronostic.name,
            'weight' : high_pronostic.weight/1000,
            'height' : high_pronostic.height/10,
            'date' : high_pronostic.date,
            'sex_score' : high_pronostic.sex_score,
            'name_score' : high_pronostic.name_score,
            'weight_score' : high_pronostic.weight_score,
            'height_score' : high_pronostic.height_score,
            'date_score' : high_pronostic.date_score,
            'total_score' : high_pronostic.total_score,
        }
        number_of_winners += 1
        high_score_pronostics.append(high_score_pronostic)
        
    print(f"Nombre de gagnants : {number_of_winners}")

    return render_template('Pronostics/pronostic_winner.html', scores_pronostics=scores_pronostics, number_of_winners=number_of_winners, high_score_pronostics=high_score_pronostics, prono_sex_btn=prono_sex_btn, user_is_admin=user_is_admin, **elements_for_base)

@views.route('/pronostic_answers', methods=['GET', 'POST'])
@login_required
def pronostic_answers():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    admin_results = get_admin_pronostic_answers()
    prono_sex_btn = admin_results['prono_sex']
    
    return render_template('Pronostics/pronostic_answers.html', admin_results=admin_results, prono_sex_btn=prono_sex_btn, **elements_for_base)

@views.route('/pronostic_all_answers', methods=['GET', 'POST'])
@login_required
def pronostic_all_answers():
    #A -----------------
    user_id = current_user.id
    #B -----------------
    elements_for_base = elements_for_base_template(user_id)
    #C -----------------
    project_in_session(user_id, elements_for_base)
    
    user_is_admin = user_is_admin_project()
    
    all_pronostics = get_pronostic_answers()
        
    return render_template('Pronostics/pronostic_all_answers.html',user_is_admin=user_is_admin, all_pronostics=all_pronostics, **elements_for_base)



#ROUTES "PHOTOS" -------------------------------------------------------------------------------------------------------------
@views.route('/photos', methods=['GET', 'POST'])
@login_required
def photos():
   # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    #D - je récupe l'info pour savoir su le user est l'admin du projet
    user_is_admin = user_is_admin_project()
    
    ok_gilles = hide_page()
    
    selected_project_id = session['selected_project']['id']
    project = Project.objects(id=selected_project_id).first()
    if not project:
        return "Project not found", 404
    
    photos = Photos.objects(project=project).order_by('-date')
    
    photos_with_unread_comments = []
    photos_to_use = []
    for photo in photos:
        if photo.utility == 'Gallery':
            photos_to_use.append(photo)
            comments = Messages.objects(photo=photo)
            
            has_unread_comments = any(current_user not in comment.seen_by_users for comment in comments)
            
            if has_unread_comments:
                photos_with_unread_comments.append(photo)
        else:
            pass
            

    return render_template('Photos/photos.html', user=current_user, ok_gilles=ok_gilles, photos_to_use=photos_to_use, photos_with_unread_comments=photos_with_unread_comments, user_is_admin=user_is_admin, **elements_for_base)
    
@views.route('/photo_and_messages/<photo_id>', methods=['GET', 'POST'])
@login_required
def photo_and_messages(photo_id):
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
        
    
    # Permet de masquer la page tant que la fonctionnalité n'est pas 100% fonctionnelle
    ok_gilles = hide_page()
    
    # Récupérer le projet sélectionné dans la session
    selected_project_id = session['selected_project']['id']
    project = Project.objects(id=selected_project_id).first()
    if not project:
        return "Project not found", 404

    # Récupérer la photo spécifique à partir de l'ID
    photo_selected = Photos.objects(id=photo_id, project=project).first()
    if not photo_selected:
        return "Photo not found", 404
    
    # Récupérer toutes les photos du projet pour le carrousel
    photos = Photos.objects(project=project).order_by('-date')
    
    #Ajouter un commentaire
    if request.method == 'POST':
        
        #Je récupe d'abord l'info concernant la photo concernée
        photo_for_message_id = request.form.get('photo_id')
        print(f"ID de la photo pour lequel je veux ajouter un message : {photo_for_message_id}")
        photo_for_message_obj = Photos.objects(id=photo_for_message_id).first()
        
        message_content = request.form.get('message')
        answer_content = (request.form.get('answer'))
        
        if message_content :
            if message_content.strip() == '':
                flash('Votre message ne peut être vide !', category='error')
                return redirect(url_for('views.photo_and_messages', photo_id=photo_for_message_id))  # Rediriger vers la photo actuelle
            
        if answer_content :
            if answer_content.strip() == '':
                flash('Votre réponse ne peut être vide !', category='error')
                return redirect(url_for('views.photo_and_messages', photo_id=photo_for_message_id))
        
        parent_message_id = request.form.get('parent_message_id')
        if parent_message_id:
            parent_message = Messages.objects(id=parent_message_id).first()
        
        
        if answer_content:
            #Créer une réponse à un message
            new_message = Messages(
            user = user_id,
            project=project,
            photo=photo_for_message_obj,
            message=answer_content,
            date=datetime.now(),
            type_message= 'Answer',
            parent_message = parent_message,
            seen_by_users = [user_id],
        )

            new_message.save()
            
            parent_message.child_message.append(new_message)
            parent_message.save()
            
        else:
            # Créer un nouvel objet message
            new_message = Messages(
            user = user_id,
            project=project,
            photo=photo_for_message_obj,
            message=message_content,
            date=datetime.now(),
            type_message= 'Message',
            seen_by_users = [user_id],
        )
            new_message.save()
                    
                
        flash('Votre message a bien été ajouté !', category='success')
        return redirect(url_for('views.photo_and_messages', photo_id=photo_for_message_id))



    photos_datas = []
    for photo in photos:
        # Récupérer les messages associés à la photo
        messages = Messages.objects(photo=photo)
        
        # Liste pour stocker les messages et leurs réponses pour cette photo
        photo_messages = []

        for message in messages:
            if message.type_message == 'Answer':
                pass
            else:
                # Récupérer les messages enfants avec leurs détails
                child_messages = []
                if message.child_message:
                    # Récupérer les objets messages enfants à partir des IDs
                    child_message_objs = Messages.objects(id__in=[child.id for child in message.child_message])
                    for child_message_obj in child_message_objs:
                        child_message_data = {
                            'user': child_message_obj.user.username if child_message_obj.user else None,
                            'message': child_message_obj.message,
                            'date': child_message_obj.date,
                        }
                        child_messages.append(child_message_data)
                
                # Créer un dictionnaire pour chaque message avec ses réponses
                message_data = {
                    'message_id': message.id,
                    'message': message.message,
                    'date': message.date,
                    'user': message.user.username if message.user else None,
                    'child_messages': child_messages
                }
                
                
                # Ajouter le message avec ses réponses à la liste des messages pour cette photo
                photo_messages.append(message_data)
        
        photo_messages.reverse()
        
        photo_data = {
            'photo_id': photo.id,
            'photo_url': photo.url_photo,
            'thumbnail_url': photo.url_thumbnail,
            'photo_description': photo.description,
            'messages': photo_messages
        }
        photos_datas.append(photo_data)
        
        
    # Trouver l'index de la photo sélectionnée
    photo_selected_index = next((index for index, photo_data in enumerate(photos_datas) if photo_data['photo_id'] == photo_selected.id), None)

    # Si l'index est trouvé, réorganiser la liste
    if photo_selected_index is not None:
        photos_datas = photos_datas[photo_selected_index:] + photos_datas[:photo_selected_index]
    
    
    #Ajout de l'id du current_user dans la liste seen_by_user des commentaires si le current_user n'avait pas déjà vu le commentaire
    # Récupérer les IDs des commentaires pour la photo sélectionnée
    displayed_message_ids = []
    messages_for_selected_photo = Messages.objects(photo=photo_selected)
    for message_obj in messages_for_selected_photo:
        displayed_message_ids.append(message_obj.id)
        
    for message_id in displayed_message_ids:
        message = Messages.objects(id=message_id).first()
        if message and current_user.id not in message.seen_by_users:
            message.update(add_to_set__seen_by_users=current_user.id)
            
    
    return render_template('Photos/photo_and_messages.html', user=current_user, ok_gilles=ok_gilles, photos_datas=photos_datas, photos=photos, **elements_for_base)

@views.route('/add_photos', methods=['GET', 'POST'])
@login_required
def add_photos():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    # Récupérer le projet sélectionné dans la session
    selected_project_id = session['selected_project']['id']
    project = Project.objects(id=selected_project_id).first()
    if not project:
        return "Project not found", 404
    
    if project:
        file = request.files.get('photo')
        description = request.form.get('description')
        if file:
            
            # --- Traitement de l'image originale ---
            # Ouvrir l'image
            image = Image.open(file)
            
            # Correction de l'orientation de l'image si nécessaire
            try:
                exif = image._getexif()
                if exif:
                    for orientation in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[orientation] == 'Orientation':
                            break
                    orientation = exif.get(orientation, None)
                    if orientation == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation == 8:
                        image = image.rotate(90, expand=True)
            except Exception as e:
                print(f"Error processing EXIF data: {e}")

            # Vérifier et appliquer le redimensionnement si nécessaire
            max_width = 1000
            if image.size[0] > max_width:
                width_percent = (max_width / float(image.size[0]))
                height_size = int((float(image.size[1]) * float(width_percent)))
                image = image.resize((max_width, height_size), Image.Resampling.LANCZOS)

            # Générer un slug pour l'URL de la photo
            brut_slug = f'{project.id}-photo-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            slug_photo = brut_slug.replace(" ", "-")

            # Sauvegarder le fichier localement dans un répertoire temporaire
            local_file_path = f'/tmp/{slug_photo}'

            # Écrire les données de l'image originale dans le fichier temporaire
            with open(local_file_path, 'wb') as f:
                image.save(f, format='JPEG')

            # --- Téléchargement de l'image originale sur Wasabi ---
            wasabi_access_key = os.getenv('WASABI_ACCESS_KEY')
            wasabi_secret_key = os.getenv('WASABI_SECRET_KEY')
            wasabi_bucket_name = 'chouxfleurs.fr'
            wasabi_endpoint_url = 'https://s3.eu-west-2.wasabisys.com'

            # Initialiser le client S3 pour Wasabi
            s3 = boto3.client(
                's3',
                endpoint_url=wasabi_endpoint_url,
                aws_access_key_id=wasabi_access_key,
                aws_secret_access_key=wasabi_secret_key,
                config=Config(signature_version='s3v4')
            )

            # Uploader le fichier vers Wasabi
            s3.upload_file(local_file_path, wasabi_bucket_name, slug_photo)

            # URL de l'image originale
            url_photo = f"{wasabi_endpoint_url}/{wasabi_bucket_name}/{slug_photo}"

            # --- Traitement de l'image redimensionnée ---

            # Redimensionner l'image
            max_width_thumbnail = 400
            width_percent = (max_width_thumbnail / float(image.size[0]))
            height_size = int((float(image.size[1]) * float(width_percent)))
            resized_image = image.resize((max_width_thumbnail, height_size), Image.Resampling.LANCZOS)

            # Sauvegarder l'image redimensionnée dans un objet BytesIO
            output = io.BytesIO()
            resized_image.save(output, format='JPEG')
            output.seek(0)

            # Générer un slug pour l'URL de la photo redimensionnée
            slug_thumbnail = f'{project.id}-thumbnail-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            slug_thumbnail = slug_thumbnail.replace(" ", "-")

            # Sauvegarder le fichier redimensionné localement
            thumbnail_file_path = f'/tmp/{slug_thumbnail}'
            with open(thumbnail_file_path, 'wb') as f:
                f.write(output.read())

            # Uploader le fichier redimensionné vers Wasabi
            s3.upload_file(thumbnail_file_path, wasabi_bucket_name, slug_thumbnail)

            # URL de l'image redimensionnée
            thumbnail_url = f"{wasabi_endpoint_url}/{wasabi_bucket_name}/{slug_thumbnail}"

            # Créer une nouvelle instance de photo et sauvegarder dans la base de données
            new_photo = Photos(
                project=project,
                url_photo=url_photo,
                utility="Gallery",
                slug_photo=slug_photo,
                url_thumbnail=thumbnail_url,
                slug_thumbnail=slug_thumbnail,
                description=description,
                date=datetime.now(),
            )
            new_photo.save()

            # Mettre à jour la liste des photos du projet
            project.photos.append(new_photo)
            project.save()

            # Supprimer les fichiers temporaires locaux
            os.remove(local_file_path)
            os.remove(thumbnail_file_path)

            flash('Votre photo a bien été ajoutée !', category='success')
            return redirect(url_for('views.photos'))

        else:
            return render_template('Photos/add_photo.html', **elements_for_base)
    else:
        flash('Vous ne pouvez pas accéder à cette page!', category='error')
        return render_template('Photos/photos.html', **elements_for_base)

@views.route('/delete_photo/<photo_id>', methods=['GET', 'POST'])
@login_required
def delete_photo(photo_id):
    # Récupérer la photo de la base de données
    photo = Photos.objects(id=photo_id).first()
    wasabi_bucket_name = 'chouxfleurs.fr'
    
    if photo:
        try:
            # Configuration pour Wasabi
            wasabi_access_key = os.getenv('WASABI_ACCESS_KEY')
            wasabi_secret_key = os.getenv('WASABI_SECRET_KEY')
            wasabi_bucket_name = 'chouxfleurs.fr'
            wasabi_endpoint_url = 'https://s3.eu-west-2.wasabisys.com'

            # Initialiser le client S3 pour Wasabi
            s3 = boto3.client(
                's3',
                endpoint_url=wasabi_endpoint_url,
                aws_access_key_id=wasabi_access_key,
                aws_secret_access_key=wasabi_secret_key,
                config=Config(signature_version='s3v4')
            )
            

            # Supprimer le fichier de Wasabi
            s3.delete_object(Bucket=wasabi_bucket_name, Key=photo.slug_photo)
            s3.delete_object(Bucket=wasabi_bucket_name, Key=photo.slug_thumbnail)
            
            
            # Supprimer la photo de la base de données
            photo.delete()
            
            flash('Photo supprimée avec succès.', category='success')
        except Exception as e:
            flash(f'Erreur lors de la suppression de la photo : {str(e)}', category='error')
            print(f'Error deleting photo: {str(e)}')
    else:
        flash('Photo introuvable.', category='error')
    
    return redirect(url_for('views.photos'))

@views.route('/change_photo_description/<photo_id>', methods=['GET', 'POST'])
@login_required
def change_photo_description(photo_id):
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    project_in_session(user_id, elements_for_base)
    
    photo = Photos.objects(id=photo_id).first()

    if request.method == 'POST':
        new_description = request.form.get('photo_description')
        photo.update(set__description=new_description)
        flash("Description modifiée avec succès !", category='success')
        return redirect(url_for('views.photo_and_messages', photo_id=photo_id)) 
        
    return render_template('Photos/change_photo_description.html', photo=photo, **elements_for_base)

@views.route('/delete_photo_description<photo_id>', methods=['POST'])
@login_required
def delete_photo_description(photo_id):
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    photo = Photos.objects(id=photo_id).first()
    
    # Supprimer l'indice concernant le nom
    photo.description = None
    photo.save()
    
    flash("Decription supprimée !", category='success')
    return redirect(url_for('views.photo_and_messages', photo_id=photo_id)) 


#ROUTES "SUIVI" -------------------------------------------------------------------------------------------------------------
@views.route('/suivi')
def suivi():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    return render_template('Suivi/suivi.html', **elements_for_base)

@views.route('/alimentation', methods=['GET', 'POST'])
def alimentation():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project = project_in_session(user_id, elements_for_base)

    if request.method == 'POST':
        # Récupérer les données du formulaire
        feeding_type = request.form.get('feeding_type')
        quantity = request.form.get('quantity') or request.form.get('aliment')
        
        modified_time = request.form.get('time')
        if modified_time :
            time = modified_time
        else:
            time = datetime.utcnow()+ timedelta(hours=2)
        
        # Créer un nouvel enregistrement pour le suivi de l'alimentation
        tracking = Tracking_food(
            user=user_id,
            project=project,
            type=feeding_type,
            quantity=quantity,
            date=time
        )
        
        # Sauvegarder l'enregistrement dans la base de données
        tracking.save()

        # Optionnel : message flash pour confirmer la sauvegarde
        flash('Les informations ont été sauvegardées avec succès.', 'success')

        # Rediriger vers la même page ou une autre page
        return redirect(url_for('views.alimentation'))

    # Récupérer toutes les occurrences concernant la nourriture
    food_trackings = Tracking_food.objects(user=user_id).all()
    food_list = [
        {
            'type': tracking.type,
            'quantity': f"{tracking.quantity} ml" if str(tracking.quantity).isdigit() else tracking.quantity,
            'date': tracking.date.strftime('%d-%m-%Y %H:%M'),
        }
        for tracking in food_trackings
    ]

    # Calcul des résumés journalier, hebdomadaire et mensuel
    
    
    # Suivi journalier -----------------------------------------------------
    today = datetime.utcnow().date()
    all_daily_food_events = Tracking_food.objects(user=user_id, date__gte=today, date__lt=today + timedelta(days=1)).all()
    # Initialiser le dictionnaire avec toutes les heures de la journée, avec `False` pour chaque heure 
    hourly_event_dict = {}
    for hour in range(24):
        hourly_event_dict[f"{hour:02d}"] = {
            'has_event':False,
        }

    daily_food_events_list = []

    for food_event in all_daily_food_events:
        daily_food_events_list.append({
            'type': food_event.type,
            'quantity': f"{food_event.quantity} ml" if str(food_event.quantity).isdigit() else food_event.quantity,
            'date': food_event.date.strftime('%d-%m-%Y %H:%M'),
        })
        
        event_hour = food_event.date.strftime('%H')
        hourly_event_dict[event_hour] = {
            'has_event':True,
            'event_type':food_event.type,
            'quantity': f"{food_event.quantity} ml" if str(food_event.quantity).isdigit() else food_event.quantity,
        }


    # Suivi hebdomadaire -----------------------------------------------------
    week_start = today - timedelta(days=today.weekday())
    weekly_trackings = Tracking_food.objects(user=user_id, date__gte=week_start, date__lt=week_start + timedelta(days=7)).all()

    def calculate_summary(trackings):
        total_quantity = 0
        total_feedings = 0
        solid_foods = defaultdict(int)
        days_with_feedings = defaultdict(int)
        
        for tracking in trackings:
            event_date = tracking.date.date()
            if tracking.type == 'biberon':
                total_quantity += int(tracking.quantity)
                total_feedings += 1
                days_with_feedings[event_date] += 1
            elif tracking.type == 'solide':
                solid_foods[tracking.quantity] += 1

        # Calcul du nombre moyen de tétées par jour
        avg_feedings_per_day = sum(days_with_feedings.values()) / len(days_with_feedings) if days_with_feedings else 0
        
        # Calcul de la quantité moyenne de biberon
        avg_bottle_quantity = total_quantity / total_feedings if total_feedings > 0 else 0
        
        # Liste des aliments solides consommés cette semaine
        solid_foods_list = [food for food, count in solid_foods.items()]

        return {
            'avg_feedings_per_day': int(avg_feedings_per_day),
            'avg_bottle_quantity': int(avg_bottle_quantity),
            'solid_foods': solid_foods_list
        }

    weekly_summary = calculate_summary(weekly_trackings)

    return render_template('Suivi/alimentation.html',
                           daily_food_events_list=daily_food_events_list,
                           hourly_event_dict=hourly_event_dict,
                           weekly_summary=weekly_summary,
                           food_list=food_list, 
                           **elements_for_base)

@views.route('/delete_alimentation/<event_id>', methods=['POST'])
def delete_alimentation(event_id):
    # Récupérer l'id de l'événement à supprimer
    try:
        # Trouver l'événement à supprimer
        event_to_delete = Tracking_food.objects(id=event_id).first()
        if event_to_delete:
            # Supprimer l'événement
            event_to_delete.delete()
            flash('L\'événement alimentaire a été supprimé avec succès.', 'success')
        else:
            flash('L\'événement alimentaire n\'existe pas.', 'error')
    except Exception as e:
        flash(f'Erreur lors de la suppression : {str(e)}', 'error')

    # Rediriger vers la même page ou une autre page
    return redirect(url_for('views.alimentation'))



#ROUTES "MY PROFIL" -------------------------------------------------------------------------------------------------------------
@views.route('/my_profil')
@login_required
def my_profil():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    user_email = current_user.email

    return render_template('My profil/my_profil.html', user=current_user, **elements_for_base, user_email=user_email)

@views.route('/change_username', methods=['GET', 'POST'])
@login_required
def change_username():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    user_username = current_user.username
    user = User.objects(id=user_id).first()

    if request.method == 'POST':
        new_username = request.form.get('new_username')

        user.username = new_username
        user.save()
        
        flash(f"Nom d'utilisateur modifié avec succès !", category='success')
        return redirect(url_for('views.my_profil'))
        
    return render_template('My profil/change_username.html', user=current_user, user_username=user_username, **elements_for_base)

@views.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    user_email = current_user.email
    user = User.objects(id=user_id).first()

    if request.method == 'POST':
        new_email = request.form.get('new_email')

        user.email = new_email
        user.save()
        
        flash(f"Adresse mail modifiée avec succès !", category='success')
        return redirect(url_for('views.my_profil'))
        
    return render_template('My profil/change_email.html', user=current_user, user_email=user_email, **elements_for_base)

@views.route('/change_notification', methods=['GET', 'POST'])
@login_required
def change_notification():
    notification_enabled = request.form.get('notification_enabled') == 'on'

    current_user.notification_enabled = notification_enabled
    current_user.save()

    flash('Paramètre de notification mis à jour avec succès!', 'success')

    return redirect(url_for('views.my_profil'))

#ROUTES "MY PROJECTS" -------------------------------------------------------------------------------------------------------------
@views.route('/my_projects', methods=['GET', 'POST'])
@login_required
def my_projects():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    current_user_18 = current_user.over_18
    user_email = current_user.email
    admin_project = Project.objects(admin=user_id).first() #J'ai l'objet project pour lequel le user actuel est l'admin
    
    projects_dict_special = elements_for_base['projects_dict'].copy()
    
    user_email = User.objects(id=user_id).first().email

    user_participations_side_project = user_participations_side_project_func()
    
    modify_project = False
    
    if admin_project: #Si le user actuel est l'admin d'un projet
        
        admin_iban = User.objects(id=user_id).first().iban
        
        user_is_admin = True
        project_id = admin_project.id
        project_name = admin_project.name
        projects_dict_special.pop(project_name) #Je retire le projet pour lequel le user actuel est l'admin de la liste des projets (utile dans la liste des projets dont il fait partie dans la page my_projects)
        
        #Je vais récupérer ici les infos concernant les participants à la liste de naissance
        user_participations = my_project_participations()
        
        #Je récupe l'info pour savoir si l'admin veut modifier son projet
        if request.method == 'POST':
            modify_project = request.form.get('modify_project_open')
            
                
        return render_template('My projects/my_projects.html', user=current_user, project_id=project_id, project_name=project_name, user_is_admin=user_is_admin, **elements_for_base, user_email=user_email, projects_dict_special=projects_dict_special, user_participations=user_participations, user_participations_side_project=user_participations_side_project, admin_iban=admin_iban, modify_project=modify_project, current_user_18=current_user_18)

    else: #Si le user actuel n'est pas l'admin d'un projet
        user_is_admin = False
        projects_dict_special = elements_for_base['projects_dict']
        
        
        return render_template('My projects/my_projects.html', user=current_user, user_is_admin=user_is_admin, **elements_for_base, user_email=user_email, projects_dict_special=projects_dict_special, user_participations_side_project=user_participations_side_project, current_user_18=current_user_18)

@views.route('/modify_my_projects')
@login_required
def modify_my_projects():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    admin_project = Project.objects(admin=user_id).first() #J'ai l'objet project pour lequel le user actuel est l'admin
    
    if admin_project: #Si le user actuel est l'admin d'un projet
        
        admin_iban = User.objects(id=user_id).first().iban

    return render_template('My projects/modify_my_projects.html', admin_iban=admin_iban, **elements_for_base)

@views.route('/participation_details', methods=['GET', 'POST'])
@login_required
def participation_details():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)   

    
    # Récupération de l'id depuis l'url ou bien depuis le formulaire (utile quand je change le statut d'une participation) par ex
    participation_id = request.args.get('participation_id')
    
    if not participation_id:
        participation_id = request.form.get('participation_id')
    
    if not participation_id:
        flash('ID de participation manquant.')
        return redirect(url_for('views.my_projects'))
    
    participation_obj = Participation.objects(id=participation_id).first()
    participation_obj_user_id = participation_obj.user.id
    user_participant = User.objects(id=participation_obj_user_id).first()
    user_participant_username = user_participant.username
    participation_project = participation_obj.project
    project_obj = Project.objects(id=participation_project.id).first()
    
    admin_id = project_obj.admin.id
    
    if user_id == admin_id:
        user_is_admin = True
    else:
        user_is_admin = False
        
    
    if not participation_obj:
        flash('Participation non trouvée.')
        return redirect(url_for('views.my_projects'))

    if request.method == 'POST':
        if request.form.get('thanks_sent'):
            participation_obj.status = "Terminé"
            participation_obj.save()
            flash(f'Vous avez confirmé avoir remercié {user_participant_username}')
            return redirect(url_for('views.participation_details', participation_id=participation_id))
        
        if request.form.get('participation_received'):
            participation_obj.status = "Reçu"
            participation_obj.save()
            flash(f'Vous avez confirmé avoir reçu la participation de {user_participant_username}!')
            return redirect(url_for('views.participation_details', participation_id=participation_id))
        
        if request.form.get('participation_send'):
            participation_obj.status = "Envoyé"
            participation_obj.save()
            flash('Vous avez confirmé avoir envoyé votre participation')
            return redirect(url_for('views.participation_details', participation_id=participation_id))
        
    user_username = participation_obj.user.username
    user_email = participation_obj.user.email
    type = participation_obj.type
    montant = participation_obj.amount
    date = participation_obj.participation_date
    date = date.strftime('%d-%m-%Y')
    status = participation_obj.status
    
    product_obj = participation_obj.product
    product_name = product_obj.name
    
    project_obj = participation_obj.project
    project_name = project_obj.name

    return render_template('My projects/participation_details.html', **elements_for_base, type=type, montant=montant, date=date, user_username=user_username, user_email=user_email, status=status, product_name=product_name, project_name=project_name, participation_id=participation_id, user_is_admin=user_is_admin)

@views.route('/iban', methods=['GET', 'POST'])
@login_required
def iban():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    user = User.objects(id=user_id).first()
    
    admin_project = Project.objects(admin=user_id).first()
    project_name = admin_project.name
    
    if request.method == 'POST':
        iban = request.form.get('iban')
        
        user.iban = iban
        user.save()
        
        flash('iban enregistré avec succès !')
        return redirect(url_for('views.modify_my_projects', **elements_for_base))
    
    
    return render_template('My projects/iban.html', user=current_user, **elements_for_base, project_name=project_name, actual_iban=user.iban)
   
@views.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        
        admin_id = current_user.id
        
        new_project = Project(
            name=project_name,
            admin=admin_id,
            users=[admin_id]
        )
        new_project.save()
        new_project_id = new_project.id
        new_project_name = new_project.name
        
        #Je viens de créer un nouveau projet, on bascule la session vers celui-ci
        session['selected_project'] = {
                'id': str(new_project_id),
                'name': new_project_name
            }
        
        flash(f'Projet "{new_project.name}" créé avec succès !', category='success')
        return redirect(url_for('views.modify_my_projects', **elements_for_base))
        
    return render_template('My projects/create_project.html', user=current_user, **elements_for_base)

@views.route('/join_project', methods=['GET', 'POST'])
@login_required
def join_project():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    

    if request.method == 'POST':
        project_to_join_link = request.form.get('project_to_join')
        
        try:
            project_to_join_id = project_to_join_link.split('=')[1].strip()[:24]
            project_exist = Project.objects(id__contains=project_to_join_id) #Je vérifie si l'id fourni fait partie des id projets existants

            admin_user_project = Project.objects(admin=user_id).first()
            
            if project_to_join_id == str(admin_user_project.id):
                flash('Vous êtes déjà l\'admin de ce projet', category='error')
                return redirect(url_for('views.join_project', **elements_for_base))

            if project_exist :
                project_to_join = Project.objects(id=project_to_join_id).first()
                project_to_join_name = Project.objects(id=project_to_join_id).first().name
                
                
                #Eléments ajoutés
                users_in_project = []
                for user in project_to_join.users:
                    users_in_project.append(str(user))
                    
                print(f"Liste des users : {users_in_project}")
                print(f"Mon id : {user_id}")
                if str(user_id) in users_in_project:
                    print('Je suis déjà dans le projet')
                    flash(f'Vous avez déjà rejoint le projet "{project_to_join_name}"', category='error')
                    return redirect(url_for('views.join_project', **elements_for_base))
                
                else:
                    project_to_join.users.append(current_user.id)
                    project_to_join.save()
                    
                    project_to_join_id = project_to_join.id
                    project_to_join_name = project_to_join.name
                    
                    session['selected_project'] = {'id': project_to_join_id, 'name': project_to_join_name}

                    flash(f'Vous avez rejoint le projet "{project_to_join_name}"', category='success')
                    return redirect(url_for('views.home_page', **elements_for_base))

            else:
                print("coucou2")
                flash('Le projet que vous souhaitez rejoindre n\'existe pas', category='error')
                return redirect(url_for('views.join_project', **elements_for_base))
            
        except (IndexError, ValueError, ValidationError):
            flash('Le projet que vous souhaitez rejoindre n\'existe pas', category='error')
            return redirect(url_for('views.join_project', **elements_for_base))
        
    else:
        return render_template('My projects/join_project.html', user=current_user, **elements_for_base)

@views.route('/rename_project', methods=['GET', 'POST'])
@login_required
def rename_project():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    project = Project.objects(admin=user_id).first()

    
    actual_name = project.name
    
    if request.method == 'POST':
        new_project_name = request.form.get('new_project_name')
        
        project.name = new_project_name
        new_project_id = project.id
        project.save()
        
        session['selected_project'] = {'id': new_project_id, 'name': new_project_name}
        
        flash(f'Nom du projet modifié avec succès !', category='success')
        return redirect(url_for('views.my_projects', **elements_for_base))
        
    return render_template('My projects/rename_project.html', user=current_user, actual_name=actual_name, **elements_for_base)

@views.route('/change_clue_due_date', methods=['GET', 'POST'])
@login_required
def change_clue_due_date():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    project = Project.objects(admin=user_id).first()
    try:
        due_date = project.due_date
        due_date = due_date.strftime('%Y-%m-%d')
    except:
        due_date = None
    

    if request.method == 'POST' :
        due_date = request.form.get('due_date')
        project.due_date = due_date
        project.save()
        
        flash(f"Date du terme mise à jour !", category='success')
        return redirect(url_for('views.change_clue_due_date'))
        
    return render_template('My projects/change_clue_due_date.html', due_date=due_date, **elements_for_base)

@views.route('/delete_clue_due_date', methods=['GET', 'POST'])
@login_required
def delete_clue_due_date():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    project = Project.objects(admin=user_id).first()
    
    # Supprimer la date du terme
    project.update(unset__due_date=True)
    flash("Date du terme supprimée avec succès !", category='success')
    return redirect(url_for('views.change_clue_due_date'))

@views.route('/change_clue_name', methods=['GET', 'POST'])
@login_required
def change_clue_name():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    project = Project.objects(admin=user_id).first()
    try:
        clue_name = project.clue_name if project.clue_name else ""
    except AttributeError:
        clue_name = ""
    
    if request.method == 'POST':
        clue_name = request.form.get('clue_name')
        project.clue_name = clue_name
        project.save()
        
        flash("Indice concernant le prénom modifié avec succès !", category='success')
        return redirect(url_for('views.change_clue_name'))
        
    return render_template('My projects/change_clue_name.html', clue_name=clue_name, **elements_for_base)

@views.route('/delete_clue_name', methods=['POST'])
@login_required
def delete_clue_name():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    project = Project.objects(admin=user_id).first()
    
    # Supprimer l'indice concernant le nom
    project.clue_name = None
    project.save()
    
    flash("Indice concernant le prénom supprimé avec succès !", category='success')
    return redirect(url_for('views.change_clue_name'))

@views.route('/delete_project', methods=['POST'])
@login_required
def delete_project():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    project = Project.objects(admin=user_id).first()
    products_in_project = project.product
    pronostics_in_project = project.pronostic
    
    products_participations = []
    pronostics_participations = []
    
    for product_id in products_in_project:
        product = Product.objects(id=(product_id)).first() #J'ai l'objet produit
        
        participations = product.participation #Je récupère la liste des participations pour ce produit
        for participation in participations:
            products_participations.append(str(participation)) #J'ajoute tous les ID des participations dans une liste

    for pronostic_id in pronostics_in_project:
        pronostics_participations.append(str(pronostic_id))
                 
            
    for user in project.users: #Pour chaque user dans le projet que je souhaite supprimer
        user_obj = User.objects(id=user).first() #Je récupe l'objet user
        
        user_participations = user_obj.participation #Je récupère la liste des participations du user
        user_pronostics = user_obj.pronostic #Je récupère la liste des pronostics du user
        
        for user_participation in user_participations: #Pour chaque participation du user
            if str(user_participation) in products_participations: #Si la participation du user est dans la liste des participations
                user_obj.update(pull__participation=user_participation) #Je retire les participations du user dans le projet à supprimer
                user_obj.save()
        
        for user_pronostic in user_pronostics:
            if str(user_pronostic) in pronostics_participations:
                user_obj.update(pull__pronostic=user_pronostic)
                # user_pronostics.remove(user_pronostic)
                user_obj.save()
          
    project.delete() #Je supprime le projet de la collection des projets
    
    session.clear()
    
    #Je vais basculer la session sur la première que je trouve pour le user actuel

    user_in_project = Project.objects(users__contains=user_id)
    if user_in_project:
        first_project = user_in_project.first() 
        first_project_id = first_project.id
        
        # Ajouter les données du premier projet trouvé dans la session
        session['selected_project'] = {
            'id': str(first_project_id),
            'name': first_project.name
            }
    else:
        flash('Projet supprimé avec succès !')
        return redirect(url_for('views.my_projects', user=current_user, **elements_for_base))
    
    flash('Projet supprimé avec succès !')
    return redirect(url_for('views.home_page', **elements_for_base))


#ROUTES AUTRES -------------------------------------------------------------------------------------------------------------
@views.route('/select_project', methods=['GET', 'POST'])
@login_required
def select_project():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    
    projects = Project.objects(users__contains=current_user.id)
    
    projects_dict = {}  
    for project in projects:
        projects_dict[project.name] = str(project.id)
        if request.method == 'POST':
            project_id = request.form.get('project_id')
            
            project_name = Project.objects(id=project_id).first().name
            session['selected_project'] = {'id': project_id, 'name': project_name}
            
            flash(f'Vous êtes maintenant connecté à "{project_name}" !')
            return redirect(url_for('views.home_page', **elements_for_base))
            
    return render_template('select_project.html', user=current_user, **elements_for_base)

@views.route('/other_data')
def other_data():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)

    
    # Rendre le template base.html avec les données spécifiques
    return render_template('base.html', **elements_for_base)

@views.route('/admin', methods=['GET', 'POST'])
def admin():
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)
    # C - Récupérer le projet actuellement sélectionné
    project_in_session(user_id, elements_for_base)
    
    if request.method == 'POST':
        pronostics = Pronostic.objects()
        for pronostic in pronostics:
            modified = False

            if isinstance(pronostic.weight, str):
                try:
                    # Conversion de la valeur en entier
                    pronostic.weight = int(pronostic.weight)
                    modified = True
                except ValueError:
                    print(f"Erreur de conversion pour le poids du pronostic {pronostic.id} avec la valeur {pronostic.weight}")

            if isinstance(pronostic.height, str):
                try:
                    # Conversion de la valeur en entier
                    pronostic.height = int(pronostic.height)
                    modified = True
                except ValueError:
                    print(f"Erreur de conversion pour la taille du pronostic {pronostic.id} avec la valeur {pronostic.height}")

            if modified:
                pronostic.save()
                print(f"Mis à jour le pronostic {pronostic.id}: weight={pronostic.weight}, height={pronostic.height}")


    # Rendre le template base.html avec les données spécifiques
    return render_template('admin.html', **elements_for_base)
    
