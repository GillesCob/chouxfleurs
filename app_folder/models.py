from flask_login import UserMixin
from mongoengine import Document, StringField, ReferenceField, CASCADE, ListField, EmailField, IntField, DateTimeField


   
class User(Document, UserMixin):
    meta = {'collection': 'users_collection'}

    email = EmailField(max_length=150, unique=True, required=True)
    password = StringField(max_length=150, required=True)
    roles = StringField(max_length=50, default='guest')
    pronostic = ListField()
    participation = ListField()


class Project(Document):
    meta = {'collection': 'projects_collection'}
    
    name = StringField(max_length=150)
    admin = ReferenceField('User', reverse_delete_rule=CASCADE)
    users = ListField()
    pronostic = ListField()
    product = ListField()


class Pronostic(Document):
    meta = {'collection': 'Pronostics_collection'}
    
    user = ReferenceField('User', reverse_delete_rule=CASCADE)
    project = ReferenceField('Project', reverse_delete_rule=CASCADE)
    sex = StringField(max_length=150, required=True)
    name = StringField(max_length=150, required=True)
    weight = StringField(max_length=150, required=True)
    height = StringField(max_length=150, required=True)
    date = StringField(max_length=150, required=True)
    
    
class Product(Document):
    meta = {'collection': 'Products_collection'}
    
    user = ReferenceField('User', reverse_delete_rule=CASCADE)
    project = ReferenceField('Project', reverse_delete_rule=CASCADE)
    name = StringField(max_length=150)
    description = StringField(max_length=150)
    price = IntField()
    already_paid = IntField()
    image = StringField(max_length=300)
    url_source = StringField(max_length=150)
    participation = ListField()
    
class Participation(Document):
    meta = {'collection': 'Participation_collection'}

    user = ReferenceField('User')
    project = ReferenceField('Project', reverse_delete_rule=CASCADE)
    product = ReferenceField('Product')
    amount = IntField()
    participation_date = DateTimeField()