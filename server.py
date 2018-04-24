from flask import Flask
from flask import render_template
from flask import request
from flask import make_response
from flask import abort, redirect, url_for

from random import randint
from collections import Counter
from async_email_sender import send_email

import json
import sqlite3

# TODO Extract DbAccess class

def get_contact_details():
    """Help me keep my privacy from github"""
    with open('./contact_details.txt') as f:
        return f.read()

def set_code(email, code):
    conn = sqlite3.connect('sqlite.db')
    c = conn.cursor()
    c.execute("INSERT INTO code VALUES (?, ?)", (email, code))
    conn.commit()

def get_code(email):
    conn = sqlite3.connect('sqlite.db')
    c = conn.cursor()
    c.execute('SELECT * FROM code WHERE email=?', (email,))

    record = c.fetchone()

    if record is None:
        return None

    return record[1]

def set_guests(email, guests):
    conn = sqlite3.connect('sqlite.db')
    c = conn.cursor()
    c.execute('''DELETE FROM rsvp WHERE email=?''', (email,))
    for guest in guests:
        c.execute('''INSERT INTO rsvp
            (firstname, lastname, isAttending, hasDiet, dietDetails, email)
            VALUES
            (?, ?, ?, ?, ?, ?)''',
            (guest['firstname'], guest['lastname'], guest['isAttending'],
             guest['hasDiet'], guest['dietDetails'], email))
    conn.commit()

def get_guests(email):
    conn = sqlite3.connect('sqlite.db')
    c = conn.cursor()

    guests = []

    for record in c.execute('SELECT * FROM rsvp WHERE email=?', (email,)):
        guests.append({
            'firstname': record[0],
            'lastname': record[1],
            'isAttending': record[2],
            'hasDiet': record[3],
            'dietDetails': record[4]
        })

    return guests

def get_guest_type_for_password(password):
    conn = sqlite3.connect('sqlite.db')
    c = conn.cursor()
    c.execute('SELECT guest_type FROM password WHERE password=?', (password,))

    record = c.fetchone()

    if record is None:
        return None

    return record[0]

# Transient state to prevent abuse
hit_counter = Counter()
sent_counter = Counter()

def make_code():
    return "{}".format(randint(1000, 9999))


app = Flask(__name__)


@app.route("/init")
def init():
    # TODO: This should be a standalone script
    conn = sqlite3.connect('sqlite.db')
    c = conn.cursor()

    try:
        c.execute('CREATE TABLE code (email, code)')
    except:
        pass

    try:
        c.execute('CREATE TABLE rsvp (firstname, lastname, isAttending, hasDiet, dietDetails, email)')
    except:
        pass

    try:
        c.execute('CREATE TABLE password (password, guest_type)')
    except:
        pass

    # INSERT INTO password vlaues ("day", "day")
    # INSERT INTO password vlaues ("evening", "evening")

    conn.commit()

    return "Database initialized"

@app.route("/reset")
def reset():
    # TODO: Is this needed in production?
    response = make_response('Your cookie has been cleared')
    response.set_cookie('guest_type', '',  expires = 0)
    response.set_cookie('email', '',  expires = 0)
    response.set_cookie('code', '',  expires = 0)
    return response

@app.route("/")
def index():
    guest_type = request.cookies.get('guest_type')

    if guest_type is not None:
        return redirect('/site')

    return render_template('index.html')

@app.route("/validate_password", methods=['POST'])
def validate_password():
    password = request.form['password'].strip().lower()

    guest_type = get_guest_type_for_password(password)

    if guest_type is None:
        response = make_response('error')
        response.set_cookie('guest_type', '',  expires = 0)
        return response

    response = make_response('success')
    response.set_cookie('guest_type', guest_type)
    return response



@app.route("/site")
def site():
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email', '')
    code = request.cookies.get('code', '')

    if guest_type is None:
        return redirect('/')

    props = {
        'day_guest': guest_type == 'day',
        'email': email,
        'code': code,
        'contact_details': get_contact_details()
    }

    return render_template('site.html', **props)

@app.route("/validate_email", methods=['POST'])
def validate_email():
    guest_type = request.cookies.get('guest_type')
    email = request.form['email'].strip().lower()
    code = request.cookies.get('code', '')

    if guest_type is None:
        return redirect('/')

    if "@" not in email:
        return 'error'

    if code != '':
        if email in hit_counter and hit_counter[email] > 3:
            return 'BLOCKED'

        if code == get_code(email):
            return 'rsvp'
        else:
            hit_counter[email] += 1

    if get_code(email) is None:
        code = make_code()
        set_code(email, code)

        send_email([email], "Your Confirmation Code", "Your code is: {}".format(code))

    response = make_response('success')
    response.set_cookie('email', email)
    response.set_cookie('code', '',  expires = 0)
    return response

@app.route("/send_again", methods=['POST'])
def send_again():
    guest_type = request.cookies.get('guest_type')
    email = request.form['email'].strip().lower()

    if guest_type is None:
        return redirect('/')

    sent_counter[email] += 1

    if sent_counter[email] > 3:
        return 'BLOCKED'

    if get_code(email) is None:
        code = make_code()
        set_code(email, code)

    code = get_code(email)

    send_email([email], "Your Confirmation Code", "Your code is: {}".format(code))

    response = make_response('success')
    return response

@app.route("/validate_code", methods=['POST'])
def validate_code():
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email')
    code = request.form['code'].strip().lower()

    if guest_type is None:
        return redirect('/')

    if email is None:
        return redirect('/site')

    if email in hit_counter and hit_counter[email] > 3:
        return 'BLOCKED'

    if code != get_code(email):
        hit_counter[email] += 1
        return 'Nope'

    response = make_response('success')
    response.set_cookie('code', code)
    return response


@app.route('/rsvp')
def rsvp():
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email')
    code = request.cookies.get('code')

    edit = bool(request.args.get('edit'))

    if guest_type is None:
        return redirect('/')

    if email is None:
        return redirect('/site')

    if code != get_code(email):
        return redirect('/site')

    if len(get_guests(email)) == 0:
        props = {
            'day_guest': guest_type == 'day',
            'email': email,
            'guests': [{} for i in range(1, 10)],
            'numGuestsSelected': 1
        }

        return render_template('new_rsvp.html', **props)

    else:
        if edit:
            guests = get_guests(email)
            props = {
                'day_guest': guest_type == 'day',
                'email': email,
                'guests': guests + [{} for i in range(len(guests) + 1, 10)],
                'numGuestsSelected': len(guests)
            }
            return render_template('new_rsvp.html', **props)
        else:
            props = {
                'day_guest': guest_type == 'day',
                'email': email,
                'guests': get_guests(email)
            }
            return render_template('existing_rsvp.html', **props)

@app.route('/update_rsvp', methods=['POST'])
def update_rsvp():
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email')
    code = request.cookies.get('code')

    if guest_type is None:
        return redirect('/')

    if email is None:
        return redirect('/site')

    if code != get_code(email):
        return redirect('/site')

    guests = json.loads(request.form['guests'])

    if len (guests) >= 10:
        return 'NOPE'

    set_guests(email, guests)
    return 'OK'
