from flask import render_template, Blueprint, session, redirect, url_for, request, flash
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app_folder.views import elements_for_base_template

from .models import User, Project, Pronostic, Product

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
    
    
    #Je supprime le projet pour lequel le user est l'admin (3)
    #Je vais également supprimer tous les pronos pour son projet (que ce soit l'objet en lui-même ou les id des pronos dans les listes des users) (2)
    #Et également toutes les participations pour son projet (que ce soit l'objet en lui-même ou les id des participations dans les listes des users) (1)
    
    project = Project.objects(admin=user_id).first()
    if project is None:
        pass
        print("Le user n'a pas créé de projet")
    else:
        products_in_project = project.product
        pronostics_in_project = project.pronostic
        
        products_participations = []
        pronostics_participations = []
        
        if products_in_project is None:
            pass
        else :
            for product_id in products_in_project:
                product = Product.objects(id=(product_id)).first() #J'ai l'objet produit
                
                participations = product.participation #Je récupère la liste des participations pour ce produit
                for participation in participations:
                    products_participations.append(str(participation)) #J'ajoute tous les ID des participations dans une liste

        if pronostics_in_project is None:
            pass
        else:
            for pronostic_id in pronostics_in_project:
                pronostics_participations.append(str(pronostic_id)) #J'ajoute tous les ID des pronostics dans une liste
                    
        if project.user is None:      
            pass
        else:
            for user in project.users: #Pour chaque user dans le projet que je souhaite supprimer
                user_obj = User.objects(id=user).first() #Je récupe l'objet user
                
                user_participations = user_obj.participation #Je récupère la liste des participations du user
                user_pronostics = user_obj.pronostic #Je récupère la liste des pronostics du user
                
                for user_participation in user_participations: #Pour chaque participation du user
                    if str(user_participation) in products_participations: #Si la participation du user est dans la liste des participations
                        user_obj.update(pull__participation=user_participation) #Je retire les participations du user dans le projet à supprimer (1)
                        user_obj.save()
                
                for user_pronostic in user_pronostics:
                    if str(user_pronostic) in pronostics_participations:
                        user_obj.update(pull__pronostic=user_pronostic) #Je retire les pronostics du user dans le projet à supprimer (2)
                        user_obj.save()
            
        project.delete() #Je supprime le projet de la collection des projets (3)
    
    #Fin de la suppression du projet pour lequel le user est l'admin
    
    
    
    user_pronostics = Pronostic.objects(user=user)
    pronostic_ids = [pronostic.id for pronostic in user_pronostics]
    
    for pronostic_id in pronostic_ids:
        Project.objects(pronostic=pronostic_id).update(pull__pronostic=pronostic_id) #Je supprime les pronostics du user dans les projets
     
    user_obj.delete()
    
    #Suppression du user dans les projets
    user_in_project = Project.objects(users=current_user.id)
    user_in_project.update(pull__users=current_user.id)
    session.clear()

    flash('Compte supprimé avec succès !', category='success')
    return redirect(url_for('auth.login'))