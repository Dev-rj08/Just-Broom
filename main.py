from flask import Flask, render_template, url_for, request, session, redirect
from pymongo import MongoClient
import bcrypt
from datetime import datetime, timedelta
from random import choice

app = Flask(__name__)

# MongoDB connection setup
client = MongoClient('mongodb+srv://dbUser1:admin@lsm.vvavvd8.mongodb.net/?retryWrites=true&w=majority')
db = client['LSM']
user_collection = db['users']
cleaning_collection = db['cleaning_options']
feedback = db['feedback_entries']
lost = db['lost_entries']

# Set the secret key for sessions
app.secret_key = 'mysecret'
app.config['UPLOAD_FOLDER'] = 'static/images'
# Basic functions

@app.route('/image/<filename>')
def get_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def get_remaining_cleanings(username):
    user = user_collection.find_one({'name': username})
    if user:
        remaining_cleanings = user.get('remaining_cleanings', 70)
        return remaining_cleanings
    else:
        return 0

def is_time_within_range(existing_time, new_time, minutes_range):
    existing_time = datetime.strptime(existing_time, "%I:%M %p")
    new_time = datetime.strptime(new_time, "%I:%M %p")
    time_difference = (new_time - existing_time).total_seconds()
    return abs(time_difference) <= minutes_range * 60

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('clean'))

    return render_template('index.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        entered_username = request.form['username']
        entered_password = request.form['pass']
        user = user_collection.find_one({'name': entered_username})

        if user and bcrypt.checkpw(entered_password.encode('utf-8'), user['password']):
            session['username'] = entered_username
            return redirect(url_for('clean'))
        return 'Invalid username/password combination'

    return render_template('login.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    room_number = "0"
    remaining_cleanings = 70

    if request.method == 'POST':
        existing_user = user_collection.find_one({'name': request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
            user_collection.insert_one({
                'name': request.form['username'],
                'password': hashpass,
                'room_number': request.form['room_number'],
                'phone_number': request.form['phone_number'],
                'remaining_cleanings': int(request.form.get('remaining_cleanings', 70))
            })

            session['username'] = request.form['username']
            return redirect(url_for('index'))

        return 'That username already exists!'

    return render_template('register.html', room_number=room_number, remaining_cleanings=remaining_cleanings)


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/clean', methods=['GET', 'POST'])
def clean():
    room_number = None
    cleaning_option = request.form.get('cleaning_option')
    selected_time = request.form.get('time_for_cleaning')

    if 'username' in session:
        user = user_collection.find_one({'name': session['username']})
        if user:
            room_number = user.get('room_number', "0")

    assigned_captain_message = ""  # Define the variable to ensure it's accessible in the entire function.

    if request.method == 'POST':
        existing_cleanings = cleaning_collection.find({
            'room_number': room_number,
            'time_for_cleaning': {'$exists': True}
        })

        for existing_cleaning in existing_cleanings:
            if is_time_within_range(existing_cleaning['time_for_cleaning'], selected_time, 1440):
                return "You cannot schedule cleaning within the next 24 hours of the existing cleaning."

        captains = {
            "Gopinath": "+1234567890",
            "Ajith": "+9876543210",
            "Vijay": "+5555555555",
            "Leo Das": "9655116789",
            "Parthiban": "69870567893",
            "Nihal Thomas": "7897656790",
            "Abdul Mohammad": "9678465792"
        }

        assigned_captain = choice(list(captains.keys()))
        assigned_captain_phone = captains[assigned_captain]

        if cleaning_option == 'broom':
            cleaning_option = 'Broom'
        elif cleaning_option == 'mop':
            cleaning_option = 'Mop'
        elif cleaning_option == 'both':
            cleaning_option = 'Both Broom and Mop'
        else:
            cleaning_option = 'Unknown'

        cleaning_data = {
            'room_number': room_number,
            'cleaning_option': cleaning_option,
            'time_for_cleaning': selected_time,
            'assigned_captain': assigned_captain,
            'captain_phone': assigned_captain_phone
        }

        assigned_captain_message = f"Captain {assigned_captain} has been assigned to clean your room at {selected_time}. Contact details {assigned_captain_phone}"

        cleaning_collection.insert_one(cleaning_data)
        remaining_cleanings = get_remaining_cleanings(session['username'])
        return f"Captain {assigned_captain} (Phone: {assigned_captain_phone}) has been assigned to clean your room {room_number} using {cleaning_option} at {selected_time}"

    remaining_cleanings = get_remaining_cleanings(session['username'])
    return render_template('clean.html', assigned_captain_message=assigned_captain_message, room_number=room_number, remaining_cleanings=remaining_cleanings)

@app.route('/events')
def events():
    return render_template('events.html') 

@app.route('/emergency')
def emergency():
    return render_template('s1.html')

@app.route('/wifi')
def wifi():
    return render_template('s2.html')

@app.route('/index_copy')
def index_copy():
    return render_template('index_copy.html')

@app.route('/feedback_form')
def feedback_form():
    return render_template('feedback_form.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback_data = {
        'name': request.form['name'],
        'email': request.form['email'],
        'feedback': request.form['complaint']
    }

    feedback.insert_one(feedback_data)

    return redirect(url_for('thank_you_feedback'))

@app.route('/thank_you_feedback')
def thank_you_feedback():
    return "Thank you for your feedback! due action will be taken regarding this! "

@app.route('/found')
def found():
    return render_template('found.html')

@app.route('/submit_item', methods=['POST'])
def submit_item():
    item_data = {
        'name': request.form['name'],
        'description': request.form['description'],
        'location': request.form['location'],
    }
    lost.insert_one(item_data)

    return redirect(url_for('thank_you_item'))

@app.route('/thank_you_item')
def thank_you_item():
    return "Thank you for submitting the item!"

if __name__ == '__main__':
    app.run(debug=True)
