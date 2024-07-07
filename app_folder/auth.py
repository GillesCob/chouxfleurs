from flask import render_template, Blueprint, session, redirect, url_for, request, flash
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app_folder.views import elements_for_base_template

from .models import User, Project, Pronostic

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
                return render_template('Auth/login.html', error="Nom d'utilisateur incorrect", count_projects=count_projects)
    return render_template('Auth/login.html', count_projects=count_projects)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    session.clear()
    count_projects = 0
    project_id = request.args.get('project_id')
    
    if current_user.is_authenticated:
        if project_id : 
                project = Project.objects(id=project_id).first()
                project_name = project.name
                current_user_id = current_user.id
                project.update(push__users=current_user_id)
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
    
    user = User.objects(id=current_user.id).first() #Je récupère le user à supprimer
    
    user_pronostics = Pronostic.objects(user=user) #Je récupère tous les Objets pronostics du user
    pronostic_ids = [pronostic.id for pronostic in user_pronostics] #Je récupère les ids des pronostics sous forme de liste    
    
    for pronostic_id in pronostic_ids:
        Project.objects(pronostic=pronostic_id).update(pull__pronostic=pronostic_id) #Je supprime les pronostics du user dans les projets
     
    user.delete()
    #Suppression du user dans les projets
    user_in_project = Project.objects(users=current_user.id)
    user_in_project.update(pull__users=current_user.id)
    session.clear()

    flash('Compte supprimé avec succès !', category='success')
    return redirect(url_for('auth.login'))