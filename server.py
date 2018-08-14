from flask import Flask
from flask import abort, redirect, url_for, request, make_response, render_template

from werkzeug.utils import secure_filename

from email_blacklist import is_legit
from random import randint
from collections import Counter
from async_email_sender import send_email

import db
import json
import os
import uuid


# Transient state to prevent abuse
hit_counter = Counter()
sent_counter = Counter()

MAX_HITS = 3  # Maximum number of times a code can be checked
MAX_SENDS = 3 # Maximum number of times an email of the code can be sent


def make_code():
    return "{}".format(randint(1000, 9999))


def get_contact_details():
    """Help me keep my privacy from github"""
    with open('./contact_details.txt') as f:
        return f.read()


def allowed_file(filename):
    ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/user_uploads')


@app.route("/reset")
def reset():
    """Reset a user's cookies. Effectively logs them out."""
    response = make_response('Your cookie has been cleared')
    response.set_cookie('guest_type', '',  expires = 0)
    response.set_cookie('email', '',  expires = 0)
    response.set_cookie('code', '',  expires = 0)
    return response


@app.route("/")
def index():
    """Returns the landing page (with password entry)"""
    if request.cookies.get('guest_type') is not None:
        return redirect('/site')

    return render_template('index.html')


@app.route("/validate_password", methods=['POST'])
def validate_password():
    """Checks the POSTed password against the database.
       Called from the landing page.
    """
    password = request.form['password'].strip().lower()
    guest_type = db.get_guest_type_for_password(password)

    if guest_type is None:
        response = make_response('error')
        response.set_cookie('guest_type', '',  expires = 0)
        return response

    response = make_response('success')
    response.set_cookie('guest_type', guest_type)
    return response


@app.route("/site")
def site():
    """Returns the main information page to the guest"""
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
    """Validates a user's email is valid.
       If the code is also set and is correct, the second level of validation
       is skipped.
    """
    guest_type = request.cookies.get('guest_type')
    email = request.form['email'].strip().lower()
    code = request.cookies.get('code', '')

    if guest_type is None:
        return redirect('/')

    if "@" not in email:
        return 'error'

    if not is_legit(email):
        print('email: {} looks fake...'.format(email))
        return 'error'

    if code != '':
        if email in hit_counter and hit_counter[email] > MAX_HITS:
            return 'BLOCKED'

        if code == db.get_code_for_email(email):
            return 'rsvp'
        else:
            hit_counter[email] += 1

    if db.get_code_for_email(email) is None:
        code = make_code()
        db.set_code_for_email(email, code)

        send_email([email], "Your Confirmation Code", "Your code is: {}".format(code))

    response = make_response('success')
    response.set_cookie('email', email)
    response.set_cookie('code', '',  expires = 0)
    return response


@app.route("/send_again", methods=['POST'])
def send_again():
    """Sends the confirmation email again.
       Used if the user is returning to the page and has forgotten their code.
    """
    guest_type = request.cookies.get('guest_type')
    email = request.form['email'].strip().lower()

    if guest_type is None:
        return redirect('/')

    sent_counter[email] += 1

    if sent_counter[email] > MAX_SENDS:
        return 'BLOCKED'

    if db.get_code_for_email(email) is None:
        code = make_code()
        db.set_code_for_email(email, code)

    code = db.get_code_for_email(email)

    send_email([email], "Your Confirmation Code", "Your code is: {}".format(code))

    response = make_response('success')
    return response


@app.route("/validate_code", methods=['POST'])
def validate_code():
    """Validates a user's email and code against what is stored in the database.
    """
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email')
    code = request.form['code'].strip().lower()

    if guest_type is None:
        return redirect('/')

    if email is None:
        return redirect('/site')

    if email in hit_counter and hit_counter[email] > MAX_HITS:
        return 'BLOCKED'

    if code != db.get_code_for_email(email):
        hit_counter[email] += 1
        return 'Nope'

    response = make_response('success')
    response.set_cookie('code', code)
    return response


@app.route('/rsvp')
def rsvp():
    """Renders the RSVP page (create, edit or view)"""
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email')
    code = request.cookies.get('code')

    edit = bool(request.args.get('edit'))

    if guest_type is None:
        return redirect('/')

    if email is None:
        return redirect('/site')

    if code != db.get_code_for_email(email):
        return redirect('/site')

    if len(db.get_guests(email)) == 0:
        props = {
            'day_guest': guest_type == 'day',
            'email': email,
            'guests': [{} for i in range(1, 10)],
            'numGuestsSelected': 1
        }

        return render_template('new_rsvp.html', **props)

    else:
        if edit:
            guests = db.get_guests(email)
            props = {
                'day_guest': guest_type == 'day',
                'email': email,
                'guests': guests + [{} for i in range(len(guests) + 1, 10)],
                'numGuestsSelected': len(guests),
                'message': db.get_message(email)
            }
            return render_template('new_rsvp.html', **props)
        else:
            props = {
                'day_guest': guest_type == 'day',
                'email': email,
                'guests': db.get_guests(email),
                'message': db.get_message(email)
            }
            return render_template('existing_rsvp.html', **props)


@app.route('/eseabrook1_report')
def report():
    """A hack to generate a report page using the templates from above"""
    password = request.args.get('password')
    if db.get_guest_type_for_password(password) != 'superuser':
        return redirect('site')

    props = {
        'day_guest': 'day',
        'email': 'None',
        'guests': db.get_all_guests(),
        'messages': db.get_all_messages()
    }
    return render_template('report.html', **props)


@app.route('/update_rsvp', methods=['POST'])
def update_rsvp():
    """Updates (or creates) the guests in the RSVP table for the specified email
    """
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email')
    code = request.cookies.get('code')

    if guest_type is None:
        return redirect('/')

    if email is None:
        return redirect('/site')

    if code != db.get_code_for_email(email):
        return redirect('/site')

    guests = json.loads(request.form['guests'])
    message = request.form['message'].strip()

    if len (guests) >= 10:
        return 'NOPE'

    db.set_guests(email, guests)
    db.set_message(email, message)
    return 'OK'


@app.route('/upload_photos', methods=['GET', 'POST'])
def upload_photos():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = '{}_{}'.format(uuid.uuid4().hex, secure_filename(file.filename))
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect('/static/user_uploads/{}'.format(filename))
    return render_template('upload.html')


@app.route('/gallery')
def list_files():
    images = [
        i for i in os.listdir(app.config['UPLOAD_FOLDER'])
        if allowed_file(i)
    ]

    props = {
        'images': images
    }

    return render_template('gallery.html', **props)
