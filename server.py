from flask import Flask
from flask import render_template
from flask import request
from flask import make_response
from flask import abort, redirect, url_for


email_to_rsvp = {}


app = Flask(__name__)

@app.route("/")
def index():
    guest_type = request.cookies.get('guest_type')

    if guest_type is not None:
        return redirect('/site')

    return render_template('index.html')

@app.route("/validate_password", methods=['POST'])
def validate_password():
    password = request.form['password']

    if password == 'day':
        response = make_response('success')
        response.set_cookie('guest_type', 'day')
        return response

    elif password == 'evening':
        response = make_response('success')
        response.set_cookie('guest_type', 'evening')
        return response

    response = make_response('error')
    response.set_cookie('guest_type', '',  expires = 0)
    return response

@app.route("/reset")
def reset():
    response = make_response('Your cookie has been cleared')
    response.set_cookie('guest_type', '',  expires = 0)
    response.set_cookie('email', '',  expires = 0)
    return response

@app.route("/site")
def site():
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email')

    if guest_type is None:
        return redirect('/')

    props = {
        'day_guest': guest_type == 'day',
        'email': email
    }

    return render_template('site.html', **props)

@app.route("/validate_email", methods=['POST'])
def validate_email():
    guest_type = request.cookies.get('guest_type')
    email = request.form['email']

    if guest_type is None:
        return redirect('/')

    response = make_response('success')
    response.set_cookie('email', email)
    return response


@app.route('/rsvp')
def rsvp():
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email')

    if guest_type is None:
        return redirect('/')

    if email is None:
        return redirect('/site')

    if email not in email_to_rsvp:
        email_to_rsvp[email] = True

        props = {
            'day_guest': guest_type == 'day',
            'email': email
        }

        return render_template('new_rsvp.html', **props)

    else:
        props = {
            'day_guest': guest_type == 'day',
            'email': email
        }

        return render_template('existing_rsvp.html', **props)


