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
    projects_dict = {project.name: project.id for project in user_projects}

    return projects_dict

def project_name_in_session():
    if 'selected_project' in session:
        current_project_name = session['selected_project']['name']
        return current_project_name

#Fonction afin de récupérer l'image du produit via les meta tags
# def get_amazon_product_image(url):
#     headers = {
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
#     }
#     response = requests.get(url, headers=headers)
#     soup = BeautifulSoup(response.content, 'html.parser')
    
#     # Chercher le meta tag 'og:image'
#     og_image_tag = soup.find('meta', property='og:image')
    
#     if og_image_tag and 'content' in og_image_tag.attrs:
#         return og_image_tag['content']
#     else:
#         return None

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
    
    
        user_is_project_admin = Project.objects(admin=user_id).first()
        
        current_project_id = session['selected_project']['id']
        current_project = Project.objects(id=current_project_id).first() #J'ai l'objet Project actuellement sauvegardé dans la session
        
        #Je souhaite maintenant récupérer les produits présents dans la Listfield "product" de mon projet
        products_for_current_project = current_project.product
        products = []
        
        for product_id in products_for_current_project:
            product = Product.objects(id=product_id).first()
            if product:
                products.append({
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    # 'image': product.image,
                    'url_source': product.url_source,
                    'already_paid':product.already_paid,
                    'id': product.id,
                    'left_to_pay': product.price-product.already_paid
                })
        
        # Trier les produits en fonction du montant restant à payer (left_to_pay)
        products = sorted(products, key=lambda x: x['left_to_pay'], reverse=True)
         
        if user_is_project_admin : #Si le user actuel est l'admin d'un projet
            user_is_admin = True
            return render_template('menu_1.html', user=current_user, user_is_admin=user_is_admin, **elements_for_base, products=products)

        else: #Si le user actuel n'est pas l'admin d'un projet
            user_is_admin = False
            return render_template('menu_1.html', user=current_user, user_is_admin=user_is_admin, **elements_for_base, products=products)
    
    
    except (KeyError, AttributeError):
        flash("Veuillez créer ou rejoindre un projet avant d'accéder aux pronostics", category='error')
        return redirect(url_for('views.my_projects', user=current_user, **elements_for_base))
    
@views.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    current_project_id = session['selected_project']['id']
    current_project = Project.objects(id=current_project_id).first()
    
    if request.method == 'POST':
        user = user_id
        project = current_project_id
        
        # url = request.form['url']
        # photo = get_amazon_product_image(url)
        
        name = request.form.get('product_name')
        description = request.form.get('product_description')
        price = request.form.get('product_price')
        # photo = request.form.get('product_photo')
        url_source = request.form.get('product_url_source')
        already_paid = 0
        
        new_product = Product(user=user, project=project, name=name, description=description, price=price, url_source=url_source, already_paid=already_paid)
        new_product.save()
        
        new_product_id = new_product.id
        
        #J'ajoute l'id du nouveau produit dans la class Project
        current_project.product.append(new_product_id)
        current_project.save()
        
        flash(f'Produit créé avec succès !', category='success')
        
        return redirect(url_for('views.menu_1'))

                
    return render_template('add_product.html',  **elements_for_base)

@views.route('/update_product/<product_id>', methods=['GET', 'POST'])
@login_required
def update_product(product_id):
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    user_is_admin=True
    
    product = Product.objects(id=product_id).first()
    
    products = []
    products.append({
                'name': product.name,
                'description': product.description,
                'price': product.price,
                # 'image': product.image,
                'url_source': product.url_source,
                'id': product.id
            })
    
    if request.method == 'POST':
        name = request.form.get('product_name')
        description = request.form.get('product_description')
        price = request.form.get('product_price')
        # photo = request.form.get('product_photo')
        url_source = request.form.get('product_url_source')
        
        if name:
            product.name = name
        if description:
            product.description = description
        if price:
            product.price = price
        # if photo:
        #     product.image = photo
        if url_source:
            product.url_source = url_source
        
        # Enregistrer les modifications
        product.save()
        
        
        flash('Produit mis à jour avec succès !')
        return redirect(url_for('views.menu_1'))
    
    return render_template('update_product.html', user=current_user, **elements_for_base, products=products, user_is_admin=user_is_admin)
  
@views.route('/product/<product_id>')
@login_required
def product_details(product_id):
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    # Récupérer les détails du produit à partir de l'ID
    product = Product.objects(id=product_id).first()
    
    left_to_pay = product.price-product.already_paid

    if product:
        return render_template('product_details.html', product=product, **elements_for_base, left_to_pay=left_to_pay)
    else:
        # Si le produit n'est pas trouvé, renvoyer une erreur 404 ou rediriger vers une autre page
        return render_template('menu_1.html', **elements_for_base), 404

@views.route('/product_participation/<product_id>')
@login_required
def product_participation(product_id):
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    # Récupérer les détails du produit à partir de l'ID
    product = Product.objects(id=product_id).first()
    
    left_to_pay = product.price-product.already_paid

    if product:
        return render_template('product_participation.html', product=product, **elements_for_base, left_to_pay=left_to_pay)
    else:
        # Si le produit n'est pas trouvé, renvoyer une erreur 404 ou rediriger vers une autre page
        return render_template('menu_1.html', **elements_for_base), 404

@views.route('/confirm_participation/<product_id>', methods=['GET','POST'])
@login_required
def confirm_participation(product_id):
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    
    current_project = session.get('selected_project')
    project_id = current_project['id']
    
    
    # Récupérer les détails du produit à partir de l'ID
    product = Product.objects(id=product_id).first()
    
    if request.method == 'POST':
        participation = request.form.get('participation_range')
        
        new_participation = Participation(user=user_id, project=project_id, product=product_id, amount=participation, participation_date=datetime.now())
        new_participation.save()
        
        product.already_paid += int(participation)
        product.participation.append(new_participation.id)
        product.save()
        
        participation_amount = new_participation.amount
        print(participation_amount)
        
        return render_template('confirm_participation.html', product=product, **elements_for_base, participation_amount=participation_amount)
    
    if product:
        return render_template('product_participation.html', product=product, **elements_for_base)
    else:
        # Si le produit n'est pas trouvé, renvoyer une erreur 404 ou rediriger vers une autre page
        return render_template('menu_1.html', **elements_for_base), 404


@views.route('/delete_product/<product_id>', methods=['GET','POST'])
@login_required
def delete_product(product_id):
    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)
    user_is_admin = True
        
    # Conversion de product_id en ObjectId
    product_id = ObjectId(product_id)
    
    # Je récupère l'objet Product concerné
    product = Product.objects(id=product_id).first()
    participation_list = product.participation
    
    for participation_id in participation_list:
        Participation.objects(id=participation_id).delete()

    
    # Suppression du produit dans les projets
    project_with_product = Project.objects(product=product_id).first()
    if project_with_product:
        project_with_product.update(pull__product=product_id)
        
        product.delete()
        flash('Produit supprimé avec succès !', category='success') 
        return redirect(url_for('views.menu_1'))

    return render_template('menu_1.html', user_is_admin=user_is_admin, **elements_for_base)

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
                        
                        return render_template('menu_2.html', user=current_user, pronostic_done=pronostic_done, prono_sex=prono_sex, prono_name=prono_name, prono_weight=prono_weight, prono_height=prono_height, prono_date=prono_date, **elements_for_base)

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
    
    #Je récupère le sexe choisi par le user afin de mettre à jour les couleurs en conséquence
    current_project_id = session['selected_project']['id'] #J'ai l'id du projet actuellement sauvegardé dans la session
    current_project = Project.objects(id=current_project_id).first() #J'ai l'objet Project actuellement sauvegardé dans la session
    pronostics_for_current_project = current_project.pronostic #J'ai la liste des pronostics pour le projet actuellement sauvegardé dans la session

    for pronostic in user.pronostic:
        if pronostic in pronostics_for_current_project:
            pronostic_utilisateur = Pronostic.objects(id=pronostic).first()
            prono_sex = pronostic_utilisateur.sex
    
    
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

    
    return render_template('all_pronostics.html', average_weight=average_weight, average_height=average_height, average_date=average_date, percentage_girl=percentage_girl, percentage_boy=percentage_boy, names=names, **elements_for_base, prono_sex=prono_sex)


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
    
    base_elements = elements_for_base_template(user_id)
    projects_dict_special = base_elements['projects_dict']
    
    
    if admin_project : #Si le user actuel est l'admin d'un projet
        user_is_admin = True
        project_id = admin_project.id
        project_name = admin_project.name
        projects_dict_special.pop(project_name) #Je retire le projet pour lequel le user actuel est l'admin de la liste des projets (utile dans la liste des projets dont il fait partie dans la page my_projects)
        
        
        #Je vais récupérer ici les infos concernant les participants à la liste de naissance
        user_participations = {}
        
        project_products= admin_project.product #Je récupère les produits du projet pour lequel mon user est l'admin
        
        for project_product in project_products: #Pour chaque produit de ce projet
            product_id = ObjectId(project_product) #Je récupère son id
            #J'ai l'id de mon produit, je vais aller chercher les id des participations pour ce produit
            product_participations = Participation.objects(product=product_id)
            
            for product_participation in product_participations:
                user = product_participation.user
                user_id = ObjectId(user.id)
                
                user_email = User.objects(id=user_id).first().email
                product_name = Product.objects(id=product_id).first().name
                amount = product_participation.amount
                date = product_participation.participation_date
                date = date.strftime('%d-%m-%Y')

                # Ajoutez la participation au dictionnaire user_participations
                if user_email not in user_participations:
                    user_participations[user_email] = []  # Créez une liste vide pour chaque nouvel utilisateur
                
                user_participations[user_email].append((user_email, product_name, amount, date))

        return render_template('my_projects.html', user=current_user, project_id=project_id, project_name=project_name, user_is_admin=user_is_admin, **base_elements, user_email=user_email, projects_dict_special=projects_dict_special, user_participations=user_participations)

    else: #Si le user actuel n'est pas l'admin d'un projet
        user_is_admin = False
        projects_dict_special = base_elements['projects_dict']
        return render_template('my_projects.html', user=current_user, user_is_admin=user_is_admin, **base_elements, user_email=user_email, projects_dict_special=projects_dict_special)

@views.route('/my_account')
@login_required
def my_account():

    user_id = current_user.id
    elements_for_base = elements_for_base_template(user_id)

    user_email = current_user.email
    project = Project.objects(admin=user_id).first() #J'ai l'objet project pour lequel le user actuel est l'admin
    
    
    
    if project : #Si le user actuel est l'admin d'un projet
        project_id = project.id
        project_name = project.name
        
        user_is_admin = True
        return render_template('my_account.html', user=current_user, project_id=project_id, project_name=project_name, user_is_admin=user_is_admin, **elements_for_base, user_email=user_email)

    else: #Si le user actuel n'est pas l'admin d'un projet
        user_is_admin = False
        
        return render_template('my_account.html', user=current_user, user_is_admin=user_is_admin, **elements_for_base, user_email=user_email)
   
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
    # Récupérer le projet actuel et le supprimer de la base de données
    user_id = current_user.id #J'ai l'id de ce user
    elements_for_base = elements_for_base_template(user_id)

    
    project = Project.objects(admin=user_id).first() #J'ai l'objet project que je souhaite supprimer pour lequel le user actuel est l'admin
    
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