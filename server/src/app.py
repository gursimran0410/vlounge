import random
from flask import Flask, request, g
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
import random
import string
import json

app = Flask(__name__)
cors = CORS(app)

app.config['SECRET_KEY'] = 'mysecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.sqlite3'
app.config['CORS_HEADERS'] = 'Content-Type'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    is_flagged = db.Column(db.Boolean(), default=False)

    # def __init__(self, name, is_flagged=False):
    #     self.name = name
    #     self.is_flagged = is_flagged

    def set_is_flagged(self, new_state):
        self.is_flagged = new_state

    def __repr__(self):
        return '<User %r>' % self.name


socketIo = SocketIO(app, cors_allowed_origins="*")

app.debug = True
app.host = 'localhost'

# database:

USERS = {}

@socketIo.on("justConnected")
def sendPeople():
    json_users = [ user.json_rep() for user in USERS.values()]
    emit("justConnected", json_users, broadcast=True)
    print("sent justConnected")

@socketIo.on("newUser")
def addUser(name):
    # update official list of users
    new_user = User(name)
    USERS[name] = new_user
    # tell others to update thier list
    emit("updateUser", new_user.json_rep(), broadcast=True)
    # add user to database
    db.session.add(new_user)
    db.session.commit()
    print("sent updateUser")

@socketIo.on("toggleFlag")
def toggleFlag(name):
    user = USERS[name]
    # update flag status in database
    user_in_db = User.query.filter_by(name=name).first()
    if user_in_db:
        user_in_db.set_is_flagged(user.is_flagged)
        db.session.commit()
    else:
        raise Exception(f'From app.py:toggleFlag() No user named {user} ')
    # print("---\n" + user.json_rep() + "\n---\n")
    emit("updateUser", user.json_rep(), broadcast=True)
    print("sent updateUser")

@app.route('/api/users', methods=['POST'])
@cross_origin()
def initialize():
    if request.method == 'POST':
        name = request.form.get("name", '')
        
        # make sure the name is unique
        while True:
            user_in_db = User.query.filter_by(name=name).first()
            if not user_in_db:
                break
            name = name + random.choice(string.digits)
        
        # create the new user and return the list with the (possibly updated) name
        new_user = User(name=name)
        db.session.add(new_user)
        db.session.commit()
        all_users = User.query.all()
        emit('newUserList', all_users, broadcast=True)
        return json.dumps({'allUsers': all_users, 'name': name})
    return {}, 200
    
   
if __name__ == '__main__':
    socketIo.run(app)
