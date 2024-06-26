from flask import render_template, Blueprint, redirect, url_for, flash, request, session
from flask_login import current_user, login_required, logout_user
from .models import Pronostic, User, Project, Product, Participation

from datetime import datetime

from bson import ObjectId

# from bs4 import BeautifulSoup
# import requests



views = Blueprint("views", __name__)


#FONCTIONS -------------------------------------------------------------------------------------------------------------
# Fonction utilisée pour créer un nouveau pronostic dans la route menu_2
def new_pronostic(user, current_project_id, current_project, pronostics_for_current_project):
    if request.method == 'POST':
        sex = request.form.get('sex')
        name = request.form.get('name')
        weight = request.form.get('weight')
        height = request.form.get('height')
        date = request.form.get('date')
        annee, mois, jour = date.split("-")
        date =  f"{jour}/{mois}/{annee}"
                
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
                            
                flash('Pronostic sauvegardé avec succès !')
                return {
                    'pronostic_done': pronostic_done,
                    'prono_sex': prono_sex,
                    'prono_name': prono_name,
                    'prono_weight': prono_weight,
                    'prono_height': prono_height,
                    'prono_date': prono_date
                }


#La navbar est évolutive en fonction de l'utilisateur connecté, des projets. Je dois lui envoyer des données et celles-ci doivent être les mêmes pour chaque route. Je crée donc une fonction qui va me permettre de récupérer ces données et de les envoyer dans chaque route. Je n'ai ainsi pas à modifier chaque route à chaque fois que je veux ajouter des éléments à la navbar.
def elements_for_base_template(user_id):
    count_projects = count_user_in_project(user_id)
    projects_dict = create_projects_dict(user_id)
    project_in_session = project_name_in_session()
        
    return {
        'count_projects' : count_projects,
        'projects_dict' : projects_dict,
        'project_name_in_session' : project_in_session
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
        project_admin_rib = User.objects(id=project_admin_id).first().rib
        projects_dict[project.name] = {
            "project_id_key": project_id,
            "admin_rib_key": project_admin_rib
        }

    return projects_dict

def project_name_in_session():
    if 'selected_project' in session:
        current_project_name = session['selected_project']['name']
        return current_project_name


#Fonction pour récupérer SA participation aux projets autres que le siens
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
            participation_date = participation_obj.participation_date #Je récupère la date de la participation
            participation_date = participation_date.strftime('%d-%m-%Y')
            
            
            # Ajoutez la participation au dictionnaire user_participations
            if project_name not in user_participations_side_project:
                user_participations_side_project[project_name] = []  # Créez une liste vide pour chaque nouvel utilisateur
            
            user_participations_side_project[project_name].append((product_name, participation_amount, participation_date))
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
    
    
    for project_product in project_products: #Pour chaque produit de ce projet
        print(f"Produit : {project_products}")
        product_id = ObjectId(project_product) #Je récupère son id
        print(f"ID du produit : {product_id}, c'est un {type(product_id)}")
        #J'ai l'id de mon produit, je vais aller chercher les id des participations pour ce produit
        product_participations = Participation.objects(product=product_id)
        
        for product_participation in product_participations:
            user = product_participation.user
            user_id = ObjectId(user.id)
            
            product_name = Product.objects(id=product_id).first().name
            participant_id = product_participation.user.id
            participant_mail = User.objects(id=participant_id).first().email
            
            if product_participation.type == "€":
                amount = product_participation.amount
                amount = f"{amount}€"
            elif product_participation.type == "donation":
                amount = "Don"
            else:
                amount = "Prêt"
            date = product_participation.participation_date
            date = date.strftime('%d-%m-%Y')

            # Ajoutez la participation au dictionnaire user_participations
            if participant_mail not in user_participations:
                user_participations[participant_mail] = []  # Créez une liste vide pour chaque nouvel utilisateur
            
            user_participations[participant_mail].append((participant_mail, product_name, amount, date))
            
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

#ROUTES -------------------------------------------------------------------------------------------------------------
@views.route('/')
@views.route('/home_page',methods=['GET'])
def home_page():
    if current_user.is_authenticated:
        user_id = current_user.id
        elements_for_base = elements_for_base_template(user_id)
        return render_template('home.html', **elements_for_base)
    
    count_projects=0
    return render_template('home.html', count_projects=count_projects)


#ROUTES "LISTE NAISSANCE" -------------------------------------------------------------------------------------------------------------
@views.route('/menu_1')
@login_required
def menu_1():
    # Elements initiaux : 
    # A - Récupérer l'id du user connecté
    user_id = current_user.id
    # B - Récupérer les éléments de base pour la navbar
    elements_for_base = elements_for_base_template(user_id)

    # Pas de projet dans la session, je récupe le premier dans lequel le user est afin d'en créer une
    if 'selected_project' not in session:
        user_in_project = Project.objects(users__contains=user_id) #user_id dans la liste users d'un projet ?
        
        if user_in_project:
            first_project = user_in_project.first() 
            
            session['selected_project'] = { #Création de la session
                'id': str(first_project.id),
                'name': first_project.name
            }
    
    try: #Si je n'ai pas de projet dans la session, erreur donc go to except
        
        #Sinon...
        
        # Objectifs ici : 
        # - Récupérer le projet dans la session
        # - Récupérer le prono concernant le sexe puis envoyer cette data dans la session
        # - Identifier si le user connecté est l'admin de ce projet
        # - Récupérer les produits de ce projet
        # - Organisation des produits en fonction du montant restant à payer
        # - Routes différentes afin de permettre ou non l'ajout de produit
        
        # -----------------
        current_project_id = session['selected_project']['id']
        current_project = Project.objects(id=current_project_id).first()
        
        # -----------------
        gender_choice = get_gender_choice(current_project)
        session['gender_choice'] = gender_choice
        
        # -----------------
        user_id = current_user.id
        admin_id = current_project.admin.id
        user_is_admin = (user_id == admin_id)
        session['admin_id'] = admin_id
        session['user_is_admin'] = user_is_admin
        
        # -----------------
        products_for_current_project = current_project.product
        
        if products_for_current_project:
            
            products = []

            for product_id in products_for_current_project:
                product = Product.objects(id=product_id).first()
                products.append({
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'url_source': product.url_source,
                    'already_paid':product.already_paid,
                    'id': product.id,
                    'left_to_pay': product.price-product.already_paid
                })
        
            # -----------------
            products = sorted(products, key=lambda x: x['left_to_pay'], reverse=True)
            
            # -----------------
            if user_is_admin :
                return render_template('menu_1.html', **elements_for_base, products=products)
            else:
                return render_template('menu_1.html', **elements_for_base, products=products)
            
        else:
            return render_template('menu_1.html', user_is_admin=user_is_admin, **elements_for_base)
    
    except (KeyError, AttributeError):
        flash("Veuillez créer ou rejoindre un projet avant d'accéder à la liste de naissance", category='error')
        return redirect(url_for('views.my_projects', **elements_for_base))
    
@views.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    #Prérequis grâce à la route menu_1
        # J'ai déjà créé une session avec : 
            # - l'id du projet actuellement sélectionné
            # - le nom du projet actuellement sélectionné
            # - le choix du sexe fait par le user actuellement connecté
            # - L'info si le user actuel est l'admin du projet actuellement sélectionné
            # - l'id de l'admin du projet

    #A -----------------
    user_id = current_user.id
    #B -----------------
    elements_for_base = elements_for_base_template(user_id)
    
    
    #Ajout d'un nouveau produit
    if request.method == 'POST':
       
        current_project_id = session['selected_project']['id']
        name = request.form.get('product_name')
        description = request.form.get('product_description')
        price = request.form.get('product_price')
        already_paid = 0
        url_source = request.form.get('product_url_source')
        
        # Création du nouveau produit avec envoi des infos précedemment collectées
        new_product = Product(project=current_project_id, name=name, description=description, price=price, url_source=url_source, already_paid=already_paid)
        new_product.save()
        
        # J'ajoute l'id du nouveau produit dans la liste des produits de mon objet Project
        current_project = Project.objects(id=current_project_id).first()
        new_product_id = new_product.id
        
        current_project.product.append(new_product_id)
        current_project.save()
        
        flash(f'Produit créé avec succès !', category='success')
        
        return redirect(url_for('views.menu_1'))
                
    return render_template('add_product.html',  **elements_for_base)

@views.route('/update_product/<product_id>', methods=['GET', 'POST'])
@login_required
def update_product(product_id):
    #Prérequis grâce à la route menu_1
        # J'ai déjà créé une session avec : 
            # - l'id du projet actuellement sélectionné
            # - le nom du projet actuellement sélectionné
            # - le choix du sexe fait par le user actuellement connecté
            # - L'info si le user actuel est l'admin du projet actuellement sélectionné

    #A -----------------
    user_id = current_user.id
    #B -----------------
    elements_for_base = elements_for_base_template(user_id)
    
    product = Product.objects(id=product_id).first()

    if request.method == 'POST':
        name = request.form.get('product_name')
        description = request.form.get('product_description')
        price = request.form.get('product_price')
        left_to_pay = request.form.get('product_left_to_pay')
        url_source = request.form.get('product_url_source')
        
        if name:
            product.name = name
        if description:
            product.description = description
        if price:
            product.price = price
        if left_to_pay:
            already_paid = product.price - int(left_to_pay)
            product.already_paid = already_paid
        if url_source:
            product.url_source = url_source
        
        product.save()
        
        flash('Produit mis à jour avec succès !')
        return redirect(url_for('views.product_details', product_id=product_id))
    
    return render_template('update_product.html', user=current_user, **elements_for_base, product=product)
  
@views.route('/product_details/<product_id>', methods=['GET','POST'])
@login_required
def product_details(product_id):
    #Prérequis grâce à la route menu_1
        # J'ai déjà créé une session avec : 
            # - l'id du projet actuellement sélectionné
            # - le nom du projet actuellement sélectionné
            # - le choix du sexe fait par le user actuellement connecté
            # - L'info si le user actuel est l'admin du projet actuellement sélectionné
            # - l'id de l'admin du projet

    #A -----------------
    user_id = current_user.id
    #B -----------------
    elements_for_base = elements_for_base_template(user_id)
    
        
    # Je récupe l'objet Product concerné
    product = Product.objects(id=product_id).first()
    
    #Je calcule le montant restant à payer
    left_to_pay = product.price-product.already_paid
    
    #Reinitialisation de cette variable à chaque fois que je charge la page
    participation = False
    
    if product:
        if request.method=='POST':
            if 'participation' in request.form:
                participation = "payment"
                return render_template('product_details.html', product=product, **elements_for_base, left_to_pay=left_to_pay, participation=participation)
            elif 'donation' in request.form:
                participation = "donation"
                return render_template('product_details.html', product=product, **elements_for_base, left_to_pay=left_to_pay, participation=participation)
            else:
                participation = "lending"
                return render_template('product_details.html', product=product, **elements_for_base, left_to_pay=left_to_pay, participation=participation)
        
        return render_template('product_details.html', product=product, **elements_for_base, left_to_pay=left_to_pay, participation=participation)
    else:
        # Si le produit n'est pas trouvé, renvoyer une erreur 404 ou rediriger vers une autre page
        return render_template('menu_1.html', **elements_for_base), 404

@views.route('/confirm_participation_loading/<product_id>', methods=['GET','POST'])
@login_required
def confirm_participation_loading(product_id):
    #Prérequis grâce à la route menu_1
    # J'ai déjà créé une session avec : 
        # - l'id du projet actuellement sélectionné
        # - le nom du projet actuellement sélectionné
        # - le choix du sexe fait par le user actuellement connecté
        # - L'info si le user actuel est l'admin du projet actuellement sélectionné
        # - l'id de l'admin du projet

    #A -----------------
    user_id = current_user.id
    #B -----------------
    elements_for_base = elements_for_base_template(user_id)
    
    #Cette page sert à enregistrer la participation du user à un produit sur la page product_details
    # J'ai la participation, j'ai l'id du produit, j'ai le projet, ... Je vais mettre tout ça dans la bdd
    
    #Le passage sur cette page est temporaire et une réorientation automatique est alors faite sur la page confirm_participation
    #Cela évite lors du rechargement de la page de renvoyer un formulaire déjà envoyé

    if request.method == 'POST':
        # Je récupe toutes les datas nécessaires à la création de la participation
        user = User.objects(id=user_id).first()
        project = session.get('selected_project', {}).get('id')
        
        type_of_participation = request.form.get('submit_btn')
        if type_of_participation == "€":
            type = "€"
            participation = request.form.get('participation_range')
        elif type_of_participation == "donation":
            type = "donation"
            participation = 0
        else:
            type = "lending"
            participation = 0

        
        new_participation = Participation(user=user_id, type=type, project=project, product=product_id, amount=participation, participation_date=datetime.now())
        new_participation.save()
        
        #J'ajoute l'id de la participation dans mon objet Product
        product = Product.objects(id=product_id).first()
        
        if type == "€":
            product.already_paid += int(participation)
            product.participation.append(new_participation.id)
        elif type == "donation" or type == "lending":
            previous_participation = product.already_paid
            value_donation = product.price - previous_participation
            product.already_paid += value_donation
            product.participation.append(new_participation.id)
            
        product.save()
        
        #J'ajoute l'id de la participation dans mon objet User
        user.participation.append(new_participation.id)
        user.save()
                
        return render_template('confirm_participation_loading.html', product=product, **elements_for_base, participation=participation,)
    
    if product:
        return render_template('product_participation.html', product=product, **elements_for_base)
    else:
        # Si le produit n'est pas trouvé, renvoyer une erreur 404 ou rediriger vers une autre page
        return render_template('menu_1.html', **elements_for_base), 404

@views.route('/confirm_participation/<participation>', methods=['GET','POST'])
@login_required
def confirm_participation(participation):
    #Prérequis grâce à la route menu_1
    # J'ai déjà créé une session avec : 
        # - l'id du projet actuellement sélectionné
        # - le nom du projet actuellement sélectionné
        # - le choix du sexe fait par le user actuellement connecté
        # - L'info si le user actuel est l'admin du projet actuellement sélectionné
        # - l'id de l'admin du projet

    #A -----------------
    user_id = current_user.id
    #B -----------------
    elements_for_base = elements_for_base_template(user_id)
    
    #Récupération du RIB de l'admin du projet
    admin_id = session['admin_id']
    admin_rib = User.objects(id=admin_id).first().rib

    return render_template('confirm_participation.html', **elements_for_base, admin_rib=admin_rib, participation = participation)

@views.route('/delete_product/<product_id>', methods=['GET','POST'])
@login_required
def delete_product(product_id):
    #Prérequis grâce à la route menu_1
    # J'ai déjà créé une session avec : 
        # - l'id du projet actuellement sélectionné
        # - le nom du projet actuellement sélectionné
        # - le choix du sexe fait par le user actuellement connecté
        # - L'info si le user actuel est l'admin du projet actuellement sélectionné
        # - l'id de l'admin du projet

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

    return redirect(url_for('views.menu_1'))

#ROUTES "PRONOS" -------------------------------------------------------------------------------------------------------------
@views.route('/menu_2', methods=['GET', 'POST'])
@login_required
def menu_2():
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)

    
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
        pronostics_for_current_project = current_project.pronostic #J'ai la liste des pronostics pour le projet actuellement sauvegardé dans la session
        if pronostics_for_current_project : #J'ai au moins 1 pronostic pour le projet sélectionné

            if current_user.pronostic : #Si le user actuel a déjà un pronostic, peut-importe sur quel projet

                for current_user_pronostic in current_user.pronostic:

                    if current_user_pronostic in pronostics_for_current_project: #Si le pronostic du user actuel est déjà lié au projet actuellement sauvegardé dans la session
                        pronostic_utilisateur = Pronostic.objects(id=current_user_pronostic).first() #J'ai l'objet Pronostic actuellement sauvegardé dans la session
                        
                        #Je récupère les datas pour les envoyer dans le html et afficher les données déjà saisies
                        prono_sex = pronostic_utilisateur.sex
                        prono_name = pronostic_utilisateur.name
                        prono_weight = pronostic_utilisateur.weight
                        prono_height = pronostic_utilisateur.height
                        prono_date = pronostic_utilisateur.date
                        pronostic_done=True
                        
                        
                        return render_template('menu_2.html', user=current_user, pronostic_done=pronostic_done, prono_sex=prono_sex, prono_name=prono_name, prono_weight=prono_weight, prono_height=prono_height, prono_date=prono_date, **elements_for_base, )

                    else : #Si le pronostic du user actuel n'est pas lié au projet actuellement sauvegardé dans la session, je créé un nouveau pronostic pour ce projet
                        result = new_pronostic(current_user, current_project_id, current_project, pronostics_for_current_project)
                        if result:
                            return render_template('menu_2.html', user=current_user, **result, **elements_for_base) #** permet de passer les données du dictionnaire result en argument de la fonction render_template
            
            else : #J'arrive ici pour faire pour la première fois un pronostic pour un projet
                result = new_pronostic(current_user, current_project_id, current_project, pronostics_for_current_project)
                if result:
                    return render_template('menu_2.html', user=current_user, **result, **elements_for_base)

        else : #J'arrive ici pour faire pour la première fois un pronostic pour un projet
            result = new_pronostic(current_user, current_project_id, current_project, pronostics_for_current_project)
            if result:
                return render_template('menu_2.html', user=current_user, **result, **elements_for_base)
            
    except (KeyError, AttributeError):
        flash("Veuillez créer ou rejoindre un projet avant d'accéder aux pronostics", category='error')
        return redirect(url_for('views.my_projects', user=current_user, **elements_for_base))
    
    return render_template('menu_2.html', user=current_user, **elements_for_base)

@views.route('/update_pronostic', methods=['GET', 'POST'])
@login_required
def update_pronostic():
    user = current_user
    
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)


    current_project_id = session['selected_project']['id'] #J'ai l'id du projet actuellement sauvegardé dans la session
    current_project = Project.objects(id=current_project_id).first() #J'ai l'objet Project actuellement sauvegardé dans la session
    pronostics_for_current_project = current_project.pronostic #J'ai la liste des pronostics pour le projet actuellement sauvegardé dans la session
    

    for pronostic in user.pronostic:
        if pronostic in pronostics_for_current_project:
            pronostic_utilisateur = Pronostic.objects(id=pronostic).first()
    
            prono_sex = pronostic_utilisateur.sex
            prono_name = pronostic_utilisateur.name
            prono_weight = pronostic_utilisateur.weight
            prono_height = pronostic_utilisateur.height
            prono_date = pronostic_utilisateur.date
            
                        
            if request.method == 'POST':
                sex = request.form.get('sex')
                name = request.form.get('name')
                weight = request.form.get('weight')
                height = request.form.get('height')
                date = request.form.get('date')
                if date:
                    annee, mois, jour = date.split("-")
                    date =  f"{jour}/{mois}/{annee}"
                
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
                prono_weight = pronostic_utilisateur.weight
                prono_height = pronostic_utilisateur.height
                prono_date = pronostic_utilisateur.date
                
                
                flash('Pronostic mis à jour avec succès !')
                return render_template('menu_2.html', user=current_user, pronostic_done=pronostic_done, prono_sex=prono_sex, prono_name=prono_name, prono_weight=prono_weight, prono_height=prono_height, prono_date=prono_date, **elements_for_base)
    
    return render_template('update_pronostic.html', user=current_user, prono_sex=prono_sex, prono_name=prono_name, prono_weight=prono_weight, prono_height=prono_height, prono_date=prono_date, **elements_for_base)

@views.route('/all_pronostics', methods=['GET', 'POST'])
@login_required
def all_pronostics():
    user = current_user
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    
    current_project_id = session['selected_project']['id']
    current_project = Project.objects(id=current_project_id).first()
    
    pronostic_ids = current_project.pronostic  # Cette liste contient les IDs des pronostics
    pronostics = Pronostic.objects(id__in=pronostic_ids)
    
    user_id = current_user.id
    
    #Je récupère le choix du sexe fait par le user afin de personnaliser les boutons des interfaces
    gender_choice = get_gender_choice(current_project)
    
    
    number_of_pronostics = len(pronostics)
    sex_girl = 0
    weight_values = []
    height_values = []
    timestamps = []
    names = {}
    for pronostic in pronostics:
         
        weight_value = float(pronostic.weight)
        weight_values.append(weight_value)
        
        height_value = float(pronostic.height)
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
    average_weight = round(average_weight, 1)

    #Taille moyenne
    average_height = sum(height_values) / len(height_values)
    average_height = round(average_height, 1)
    
    #Date moyenne
    average_timestamp = sum(timestamps) / len(timestamps)
    average_date = datetime.fromtimestamp(average_timestamp)
    average_date = average_date.strftime('%d-%m-%Y')

    #Pourcentage de filles/gars
    percentage_girl = int(round((sex_girl*100)/number_of_pronostics,0))
    percentage_boy = int(round(100 - percentage_girl,0))
    
    #Tris des prénoms avec ceux proposés plusieurs fois en premier
    names = dict(sorted(names.items(), key=lambda item: item[1], reverse=True))

    
    return render_template('all_pronostics.html', average_weight=average_weight, average_height=average_height, average_date=average_date, percentage_girl=percentage_girl, percentage_boy=percentage_boy, names=names, **elements_for_base, gender_choice=gender_choice)


#ROUTES "PHOTOS" -------------------------------------------------------------------------------------------------------------
@views.route('/menu_3')
@login_required
def menu_3():
    user_id = current_user.id #J'ai l'id du user actuellement connecté
    elements_for_base = elements_for_base_template(user_id)

    project = Project.objects(admin=user_id).first() #J'ai l'objet project pour lequel le user actuel est l'admin
    
    if project : #Si le user actuel est l'admin d'un projet
        project_name = project.name
        
        user_is_admin = True
        return render_template('menu_3.html', user=current_user, project_name=project_name, user_is_admin=user_is_admin, **elements_for_base)

    else: #Si le user actuel n'est pas l'admin d'un projet
        user_is_admin = False
        return render_template('menu_3.html', user=current_user, user_is_admin=user_is_admin, **elements_for_base)


#ROUTES "MON COMPTE" -------------------------------------------------------------------------------------------------------------
@views.route('/my_profil')
@login_required
def my_profil():
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)

    user_email = current_user.email

    return render_template('my_profil.html', user=current_user, **elements_for_base, user_email=user_email)

@views.route('/my_projects', methods=['GET', 'POST'])
@login_required
def my_projects():
    user_id = current_user.id
    user_email = current_user.email
    admin_project = Project.objects(admin=user_id).first() #J'ai l'objet project pour lequel le user actuel est l'admin
    
    elements_for_base = elements_for_base_template(user_id)
    projects_dict_special = elements_for_base['projects_dict'].copy()
    
    user_email = User.objects(id=user_id).first().email

    user_participations_side_project = user_participations_side_project_func()
    
    modify_project = False
    
    if admin_project: #Si le user actuel est l'admin d'un projet
        
        admin_rib = User.objects(id=user_id).first().rib
        
        user_is_admin = True
        project_id = admin_project.id
        project_name = admin_project.name
        projects_dict_special.pop(project_name) #Je retire le projet pour lequel le user actuel est l'admin de la liste des projets (utile dans la liste des projets dont il fait partie dans la page my_projects)
        
        #Je vais récupérer ici les infos concernant les participants à la liste de naissance
        user_participations = my_project_participations()
        
        #Je récupe l'info pour savoir si l'admin veut modifier son projet
        if request.method == 'POST':
            modify_project = request.form.get('modify_project_open')
                
        return render_template('my_projects.html', user=current_user, project_id=project_id, project_name=project_name, user_is_admin=user_is_admin, **elements_for_base, user_email=user_email, projects_dict_special=projects_dict_special, user_participations=user_participations, user_participations_side_project=user_participations_side_project, admin_rib=admin_rib, modify_project=modify_project)

    else: #Si le user actuel n'est pas l'admin d'un projet
        user_is_admin = False
        projects_dict_special = elements_for_base['projects_dict']
        
        
        return render_template('my_projects.html', user=current_user, user_is_admin=user_is_admin, **elements_for_base, user_email=user_email, projects_dict_special=projects_dict_special, user_participations_side_project=user_participations_side_project)

@views.route('/rib', methods=['GET', 'POST'])
@login_required
def rib():
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    
    user = User.objects(id=user_id).first()
    
    admin_project = Project.objects(admin=user_id).first()
    project_name = admin_project.name
    
    if request.method == 'POST':
        rib = request.form.get('rib')
        
        user.rib = rib
        user.save()
        
        flash('RIB enregistré avec succès !')
        return redirect(url_for('views.my_projects', **elements_for_base))
    
    
    return render_template('rib.html', user=current_user, **elements_for_base, project_name=project_name, actual_rib=user.rib)
   
@views.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)

    
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
        return redirect(url_for('views.menu_2', **elements_for_base))
        
    return render_template('create_project.html', user=current_user, **elements_for_base)

@views.route('/join_project', methods=['GET', 'POST'])
@login_required
def join_project():
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)

    
    if request.method == 'POST':
        project_to_join_link = request.form.get('project_to_join')
        print("coucou")
        
        try: #je gère les erreurs notamment si je n'ai pas de "=" dans le lien
            project_to_join_id = project_to_join_link.split('=')[1].strip()[:24] #je récupère les 24 premiers caractères après le "="
            
            project_exist = Project.objects(id__contains=project_to_join_id) #Je vérifie si l'id fourni fait partie des id projets existants
            
            if project_exist :
                project_to_join = Project.objects(id=project_to_join_id).first()
                project_to_join_name = Project.objects(id=project_to_join_id).first().name
            
                if current_user.id in project_to_join.users:
                    flash(f'Vous avez déjà rejoint le projet "{project_to_join_name}"', category='error')
                    return redirect(url_for('views.my_account', **elements_for_base))
                
                else:
                    project_to_join.users.append(current_user.id)
                    project_to_join.save()
                    
                    project_to_join_id = project_to_join.id
                    project_to_join_name = project_to_join.name
                    
                    session['selected_project'] = {'id': project_to_join_id, 'name': project_to_join_name}

                    flash(f'Vous avez rejoint le projet "{project_to_join_name}"', category='success')
                    return redirect(url_for('views.home_page', **elements_for_base))

            else:
                flash('Le projet que vous souhaitez rejoindre n\'existe pas', category='error')
                return redirect(url_for('views.my_account'))
            
        except (IndexError):
            flash('Le projet que vous souhaitez rejoindre n\'existe pas', category='error')
            return redirect(url_for('views.my_account', **elements_for_base))
        
    else:
        return render_template('join_project.html', user=current_user, **elements_for_base)

@views.route('/select_project', methods=['GET', 'POST'])
@login_required
def select_project():
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    
    
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

@views.route('/rename_project', methods=['GET', 'POST'])
@login_required
def rename_project():
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)

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
        
    return render_template('rename_project.html', user=current_user, actual_name=actual_name, **elements_for_base)

@views.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email():
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)

    user_email = current_user.email
    user = User.objects(id=user_id).first()

    
    
    if request.method == 'POST':
        new_email = request.form.get('new_email')

        user.email = new_email
        user.save()
        
                
        flash(f"Adresse mail modifiée avec succès !", category='success')
        return redirect(url_for('views.my_account', **elements_for_base, user_email=user_email))
        
    return render_template('change_email.html', user=current_user, user_email=user_email, **elements_for_base)

@views.route('/delete_project', methods=['POST'], )
@login_required
def delete_project():
    user_id = current_user.id #J'ai l'id de ce user
    elements_for_base = elements_for_base_template(user_id)

    #Récupération de toutes les participations pour le projet en cours
    project = Project.objects(admin=user_id).first() #Récup du projet
    
    products_in_project = project.product #Récup de la liste des produits du projet
    products_participations = []
    
    pronostics_in_project = project.pronostic #Récup de la liste des pronostics du projet
    pronostics_participations = []
    
    for product_id in products_in_project:
        product = Product.objects(id=(product_id)).first() #J'ai l'objet produit
        
        participations = product.participation #Je récupère la liste des participations pour ce produit
        
        for participation in participations:
            products_participations.append(str(participation)) #J'ajoute toutes les participations dans une liste
            
    for pronostic in pronostics_in_project:
        pronostics_participations.append(str(pronostic))
                 
            
            
    for user in project.users: #Pour chaque user dans le projet que je souhaite supprimer
        user_obj = User.objects(id=user).first()
        
        user_participations = user_obj.participation #Je récupère la liste des participations pour ce user
        user_pronostics = user_obj.pronostic #Je récupère la liste des pronostics pour ce user
        for user_participation in user_participations:
            if user_participation == participation: #Si la participation du user est dans la liste des participations du projet
                user_participations.remove(user_participation)
                user_obj.save()
        for user_pronostic in user_pronostics:
            if user_pronostic == pronostic:
                user_pronostics.remove(user_pronostic)
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
        flash("Veuillez créer ou rejoindre un projet avant d'accéder aux pronostics", category='error')
        return redirect(url_for('views.my_projects', user=current_user, **elements_for_base))
    
    flash('Projet supprimé avec succès !', category='success')
    return redirect(url_for('views.home_page', **elements_for_base))

@views.route('/other_data')
def other_data():
    user_id = current_user.id #J'ai l'id du user actuellement connecté
    elements_for_base = elements_for_base_template(user_id)

    
    # Rendre le template base.html avec les données spécifiques
    return render_template('base.html', **elements_for_base)