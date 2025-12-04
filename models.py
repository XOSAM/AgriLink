from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, email, name, role):
        self.id = id
        self.email = email
        self.name = name
        self.role = role