import sys
import os
sys.path.append('c:/Users/jawad/Downloads/PLPG Github/PLPG/backend-python')
from app import app
from flask_jwt_extended import create_access_token
import jwt

with app.app_context():
    token = create_access_token(identity="1234567890")
    print("TOKEN:", token)
    decoded = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
    print("DECODED:", decoded)
