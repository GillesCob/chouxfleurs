# @views.route('/new_route')
# @login_required
# def new_route():
# #Fonctions afin d'initialiser la route
#     #-----------------------------------
#     user_id = current_user.id
#     elements_for_base = elements_for_navbar(user_id)
#     add_project_in_session(user_id)
#     project_exist = add_project_in_session(user_id)
#     if project_exist == False:
#         return redirect(url_for('views.my_projects'))
#     #-----------------------------------
    
# #Fonctions afin de récupérer les infos nécessaires + variables tirées de ces fonctions

# #Initialisation des variables

# #--------------------------------------------------------------------------------------------------------------------------------------------
# #Début du code pour la route "new_route"
# #--------------------------------------------------------------------------------------------------------------------------------------------

#     return render_template('new_route.html', **elements_for_base)