from flask import render_template, Blueprint, session, redirect, url_for, request, flash
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app_folder.views import elements_for_base_template

from .models import User, Project, Pronostic, Product, Participation

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
    elements_for_base = elements_for_base_template(user_id)

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
    
    
    #Je vais d'abord m'occuper du projet pour lequel le user est l'admin avec dans l'ordre :
        #I - Je m'occupe de mettre à jour les listes de pronostic et de participation pour chaque user du projet à supprimer
            #1 - Listing des ID de tous les produits (ObjectID)
            #2 - Listing des ID de tous les pronostics (ObjectID)
            #3 - Listing des ID de tous les users (ObjectID)
            
            #4 - Listing des ID de toutes les participations pour chaque produits (STR)
            #5 - Listing des ID de tous les pronostics (STR)
            
            #6 - Liste de l'ensemble des participations du user (ObjectID)
            #7 - Liste de l'ensemble des pronostics du user (ObjectID)
            
            #8 - Si une participation du user(#6) est dans la liste des participations du projet(#4), je la retire
            #9 - Si un pronostic du user(#7) est dans la liste des pronostics du projet(#5), je le retire
            
            #10 - Je supprime le projet ce qui en cascade supprime 
                # - Les pronostics
                # - Les produits
                # - Les participations
            
        #II - Le user a pu participer à des projets. Je dois donc supprimer ses pronos, ses participations à des produits et sa présence dans les projets
            #11 - Listing des ID de tous les pronostics du user (ObjectID)
            #12 - Suppression de tous les pronostics du user pour l'ensemble des projets
            #13 - Listing de tous les projets dans lesquels le user est présent
            #14 - Suppression de la présence du user dans l'ensemble des projets
            #15 - Listing de toutes les participations du user
            #16 - Identification des produits auxquels le user a participé
            #17 - Mettre à jour le already_paid des produits en fonction de la participation du user
            #18 - Mettre  à jour le statut du produit : si participation du user != "€" alors type = €
            #19 - Retirer la participation du user du produit
            
        #III - Suppression du user
    
    
    project = Project.objects(admin=user_id).first()
    if project is None:
        pass
    else:
        product_list = project.product #1
        pronostic_list = project.pronostic #2
        user_list = project.users #3
        
        participations_list_str = []
        pronostics_list_str = []
        
        if product_list is None:
            pass
        else :
            for product_id in product_list: #4
                product = Product.objects(id=(product_id)).first()
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
                user_obj = User.objects(id=user).first()
                
                user_participations = user_obj.participation #6
                user_pronostics = user_obj.pronostic #7
                
                for user_participation in user_participations:
                    if str(user_participation) in participations_list_str:
                        user_obj.update(pull__participation=user_participation) #8
                        user_obj.save()
                
                for user_pronostic in user_pronostics:
                    if str(user_pronostic) in pronostics_list_str:
                        user_obj.update(pull__pronostic=user_pronostic) #9
                        user_obj.save()
            
        project.delete() #10
    
    
    
    
    user_pronostics = Pronostic.objects(user=user_obj) #11
    if user_pronostics is None:
        pass
    else:
        pronostic_ids = [pronostic.id for pronostic in user_pronostics]
        for pronostic_id in pronostic_ids:
            Project.objects(pronostic=pronostic_id).update(pull__pronostic=pronostic_id) #12
    
    user_in_project = Project.objects(users=user_id) #13
    user_in_project.update(pull__users=user_id) #14
    
    
    user_participations = Participation.objects(user=user_obj) #15
    if user_participations is None:
        pass
    else:
        participation_ids = [participation.id for participation in user_participations]
        for participation_id in participation_ids:
            participation = Participation.objects(id=participation_id).first()
            product = Product.objects(participation=participation_id).first() #16
            
            if product : 
                product.already_paid -= participation.amount #17
                if participation.type != "€": #18
                    product.type = "€"
                    
                product.update(pull_participation=participation_id) #19
                product.save()
                
                
    user_obj.delete() #III

    flash('Compte supprimé avec succès !', category='success')
    return redirect(url_for('auth.login'))