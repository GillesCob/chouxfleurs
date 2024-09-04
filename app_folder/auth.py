from flask import render_template, Blueprint, session, redirect, url_for, request, flash
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app_folder.views import elements_for_navbar

from .models import User, Project, Pronostic, Product, Participation

from bson import ObjectId


auth = Blueprint("auth", __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()
    count_projects = 0
    
    if current_user.is_authenticated:
        return render_template('Home page/home.html', user=current_user, count_projects=count_projects)
    else:
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = User.objects(email=email).first()     
            
            if user :
                if check_password_hash(user.password, password):
                    project_id = request.args.get('project_id')
            
                    if project_id : 
                        project = Project.objects(id=project_id).first()
                        project_name = project.name
                        user_id = user.id
                        project.update(push__users=user_id)
                        flash(f'Projet {project_name} rejoint avec succès !', category='success')
                        login_user(user, remember=True)
                        
                        session['selected_project'] = {
                        'id': str(project.id),
                        'name': project.name
                        }
                        return redirect(url_for('views.pronostic', count_projects=count_projects))
                    
                    else:
                        login_user(user, remember=True)
                        return redirect(url_for('views.home_page'))
                else:
                    return render_template('Auth/login.html', error="Mauvais mot de passe !", count_projects=count_projects)
            
            else:
                return render_template('Auth/login.html', error="Cet email ne possède pas de compte", count_projects=count_projects)
        
    return render_template('Auth/login.html', count_projects=count_projects)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    session.clear()
    count_projects = 0
    project_id = request.args.get('project_id')
    
    if current_user.is_authenticated:
        if project_id : 
                project = Project.objects(id=project_id).first()
                project_users = project.users
                if current_user.id in project_users:
                    flash('Vous avez déjà rejoint ce projet', category='info')
                    return redirect(url_for('views.home_page'))
                else:
                    project_name = project.name
                    project.update(push__users=current_user.id)
                    flash(f'Vous avez rejoins "{project_name}"')
                    return redirect(url_for('views.home_page'))
                
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        over_18_checkbox = request.form.get('over_18')
        if over_18_checkbox == 'on':
            over_18 = True
        else:
            over_18 = False
        
        user = User.objects(email=email).first()
        
        if user:
            return render_template('Auth/register.html', error='Cet utilisateur existe déjà', count_projects=count_projects)
        
        if len(email) < 4:
            return render_template('Auth/register.html', error='Le nom d\'utilisateur doit contenir au moins 4 caractères', count_projects=count_projects)
        
        if len(password) < 4:
            return render_template('Auth/register.html', error='Le mot de passe doit contenir au moins 4 caractères', count_projects=count_projects)
        
        if password == confirm_password:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password=hashed_password, over_18=over_18)              
                    
            new_user.save()
            
            # send_confirmation_email(new_user.email)
            # flash('Un email de confirmation a été envoyé. Veuillez vérifier votre boîte de réception.', category='info')
            
            
            
            if project_id : 
                project = Project.objects(id=project_id).first()
                project_name = project.name
                new_user_id = new_user.id
                project.update(push__users=new_user_id)
                flash(f'Compte créé ! Connectez-vous pour rejoindre "{project_name}"')
                return redirect(url_for('auth.login'))
                        
            flash(f'Compte créé avec succès !', category='success')
            return redirect(url_for('auth.login'))
        
        else:
            return render_template('Auth/register.html', error='Les mots de passe ne correspondent pas', count_projects=count_projects)
        
    return render_template('Auth/register.html', count_projects=count_projects)

@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    user_id = current_user.id
    elements_for_base = elements_for_navbar(user_id)

    user = User.objects(id=user_id).first()

    
    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if len(new_password) < 4:
            return render_template('Auth/register.html', error='Le mot de passe doit contenir au moins 4 caractères')
        
        if new_password == confirm_password:
            hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
            user.password = hashed_password
        
            user.save()
        
            flash(f"Mot de passe modifié avec succès !", category='success')
        return redirect(url_for('views.my_profil', **elements_for_base))
        
    return render_template('Auth/change_password.html', user=current_user, **elements_for_base)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnecté avec succès !', category='success')
    return redirect(url_for('auth.login'))

@auth.route('/delete', methods=['POST'])
@login_required
def delete_account():
    user_obj = User.objects(id=current_user.id).first()
    user_id = user_obj.id
    

    #Je vais d'abord m'occuper du projet pour lequel le user est l'admin :
        #I - Je m'occupe de mettre à jour les listes de pronostic et de participation pour chaque user du projet à supprimer
            #1 - Listing des ID de tous les produits du projet à supprimer (ObjectID)
            #2 - Listing des ID de tous les pronostics du projet à supprimer (ObjectID)
            #3 - Listing des ID de tous les users du projet à supprimer (ObjectID)
            
            #4 - Listing des ID de toutes les participations pour chaque produits (STR)
            #5 - Listing des ID de tous les pronostics (STR)
            
            #6 - Liste de l'ensemble des participations du user (ObjectID)
            #7 - Liste de l'ensemble des pronostics du user (ObjectID)
            
            #8 - Si une participation du user(#6) est dans la liste des participations du projet(#4), je la retire de sa liste
            #9 - Si un pronostic du user(#7) est dans la liste des pronostics du projet(#5), je le retire de sa liste
            
            #10 - Je supprime le projet ce qui en cascade supprime 
                # - Les objets pronostics
                # - Les objets produits
                # - Les objets participations
            
        #II - Le user a pu participer à des projets. Je dois donc supprimer ses infos dans les projets (id de ses pronos) + La trace de ses participations dans les produits 
            #11 - Listing de tous les projets dans lesquels le user est présent
            #12 - Suppression de la présence du user dans la liste des users pour chaque projet
            #13 - Suppression de ses pronos dans les listes des projets
            #14 - Listing de toutes les participations du user
            #15 - La participation a été envoyée ou reçu. Je ne vais pas la supprimer mais plutôt l'attribuer à un profil "user_deleted"
            #16 - Si la participation est financie, je retire sa promesse du montant "already_paid" du produit
            #117 - Si Don ou Prêt, "already_paid" = 0 et "type" = € pour le produit
            
        #III - Suppression du user ce qui en cascade supprime
            # - Ses objets pronostics
            # - Ses objets participations

   
 #I --------------------------------------------------------------------------------------------------------------------
    project_to_delete = Project.objects(admin=user_id).first()
    if project_to_delete is None:
        pass
    else:
        product_list = project_to_delete.product #1
        pronostic_list = project_to_delete.pronostic #2
        user_list = project_to_delete.users #3
        
        participations_list_str = []
        pronostics_list_str = []
        
        if product_list is None:
            pass
        else :
            for product_id in product_list: #4
                product = Product.objects(id=product_id).first()
                participations = product.participation
                for participation in participations:
                    participations_list_str.append(str(participation))

        if pronostic_list is None:
            pass
        else:
            for pronostic_id in pronostic_list: #5
                pronostics_list_str.append(str(pronostic_id))


        if user_list is None:
            pass
        else:
            for user in user_list:
                user_obj_2 = User.objects(id=user).first()
                user_participations = user_obj_2.participation #6
                user_pronostics = user_obj_2.pronostic #7
                
                if user_participations is None:
                    pass
                else:
                    for user_participation in user_participations:
                        if str(user_participation) in participations_list_str:
                            user_obj_2.update(pull__participation=user_participation) #8
                            user_obj_2.save()
                
                if user_pronostics is None:
                    pass
                else:
                    for user_pronostic in user_pronostics:
                        if str(user_pronostic) in pronostics_list_str:
                            user_obj_2.update(pull__pronostic=user_pronostic) #9
                            user_obj_2.save()
                            
        project_to_delete.delete() #10
 

#II --------------------------------------------------------------------------------------------------------------------
    user_in_projects = Project.objects(users=user_id) #11
    if user_in_projects is None:
        pass
    else:
        for user_in_project in user_in_projects:
            project_obj = Project.objects(id=user_in_project.id).first()
            project_obj.update(pull__users=user_id) #12
            
    user_pronostics = Pronostic.objects(user=user_obj) #13
    if user_pronostics is None:
        pass
    else:
        for user_pronostic in user_pronostics:
            pronostic_obj = Pronostic.objects(id=user_pronostic.id).first()
            project_obj = Project.objects(id=pronostic_obj.project.id).first()
            project_obj.update(pull__pronostic=pronostic_obj.id)
            project_obj.save()
    
    
    user_participations = Participation.objects(user=user_obj) #14
    if user_participations is None:
        pass
    else:
        for user_participation in user_participations:
            participation_obj = Participation.objects(id=user_participation.id).first()
            product_obj = Product.objects(id=participation_obj.product.id).first()
            if participation_obj.status != "Promesse": #15 (Envoyé, Reçu ou Terminé)
                user_deleted = User.objects(id="668d5309f35b522f8889194c").first()
                participation_id = str(participation_obj.id)
                user_deleted.participation.append(ObjectId(participation_id))
                user_deleted.save()
                participation_obj.user = user_deleted
                participation_obj.save()
            else:
                if participation_obj.type == "€": #16
                    participation_amount = participation_obj.amount
                    product_obj.already_paid -= participation_amount
                else :
                    product_obj.type = "€" #17
                    product_obj.already_paid = 0
                
                product_obj.update(pull__participation=participation_obj.id)
                product_obj.save()

#III --------------------------------------------------------------------------------------------------------------------
    user_obj.delete()

    flash('Compte supprimé avec succès !', category='success')
    return redirect(url_for('views.home_page'))