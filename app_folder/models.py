from flask_login import UserMixin
from mongoengine import Document, StringField, ReferenceField, CASCADE, ListField, EmailField, IntField, DateTimeField, BooleanField


   
class User(Document, UserMixin):
    meta = {'collection': 'users_collection'}

    username = StringField(max_length=20, required=True)
    email = EmailField(max_length=150, unique=True, required=True)
    password = StringField(max_length=150, required=True)
    over_18 = BooleanField(default=False)
    roles = StringField(max_length=50, default='guest')
    pronostic = ListField()
    participation = ListField()
    iban = StringField(max_length=150)
    validationCode = StringField(max_length=150)
    is_validated = BooleanField(default=False)


class Project(Document):
    meta = {'collection': 'projects_collection'}
    
    name = StringField(max_length=20)
    admin = ReferenceField('User', reverse_delete_rule=CASCADE)
    users = ListField()
    due_date = DateTimeField()
    pronostic = ListField()
    product = ListField()
    end_pronostics = BooleanField(default=False)
    clue_name = StringField(max_length=150)


class Pronostic(Document):
    meta = {'collection': 'Pronostics_collection'}
    
    user = ReferenceField('User', reverse_delete_rule=CASCADE)
    project = ReferenceField('Project', reverse_delete_rule=CASCADE)
    sex = StringField(max_length=150, required=True)
    name = StringField(max_length=150, required=True)
    weight = IntField(required=True)
    height = IntField(required=True)
    date = StringField(max_length=150, required=True)
    sex_score = IntField()
    name_score = IntField()
    weight_score = IntField()
    height_score = IntField()
    date_score = IntField()
    total_score = IntField()
    
    
class Product(Document):
    meta = {'collection': 'Products_collection'}
    
    project = ReferenceField('Project', reverse_delete_rule=CASCADE)
    name = StringField(max_length=50)
    description = StringField(max_length=150)
    price = IntField()
    already_paid = IntField()
    url_source = StringField(max_length=150)
    image_url = StringField(max_length=150)
    participation = ListField()
    type = StringField(max_length=150)
    
    
class Participation(Document):
    meta = {'collection': 'Participation_collection'}

    user = ReferenceField('User', reverse_delete_rule=CASCADE)
    project = ReferenceField('Project', reverse_delete_rule=CASCADE)
    type = StringField(max_length=150)
    product = ReferenceField('Product')
    amount = IntField()
    participation_date = DateTimeField()
    status = StringField(max_length=150)