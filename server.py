from flask import Flask
from flask import render_template
from flask import request
from flask import make_response
from flask import abort, redirect, url_for
import json

from multiprocessing import Pool # Here are the big guns

from random import randint
from collections import Counter

import sqlite3

import smtplib

email_to_rsvp = {}


app = Flask(__name__)

def get_password():
    with open('./password.txt') as f:
	return f.readline()

def callback(arg):
    print arg

def send_email(to, subject, body):
    """
    to - Array of email addresses
    subject & body - duh
    """
    gmail_user = 'bethan.and.edward.wedding@gmail.com'
    gmail_password = get_password()

    sent_from = "Bethan & Edward's Wedding"

    email_text = "From: {}\nTo: {}\nSubject: {}\n\n{}".format(
	sent_from, ", ".join(to), subject, body)

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    server.login(gmail_user, gmail_password)
    server.sendmail(sent_from, to, email_text)
    server.close()

email_thread_pool = Pool(processes=1)


@app.route("/init")
def init():
    conn = sqlite3.connect('sqlite.db')
    c = conn.cursor()
    return "Database initialized"


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
    code = request.cookies.get('code', '')

    if guest_type is None:
        return redirect('/')

    props = {
        'day_guest': guest_type == 'day',
        'email': email,
        'code': code
    }

    return render_template('site.html', **props)

code_map = {}
hit_counter = Counter()

def make_code():
    return "{}".format(randint(1000, 9999))

@app.route("/validate_email", methods=['POST'])
def validate_email():
    guest_type = request.cookies.get('guest_type')
    email = request.form['email']

    if guest_type is None:
        return redirect('/')

    if email not in code_map:
        code = make_code()
        code_map[email] = code

        e = ([email], "Your Confirmation Code", 'Your code is: {}'.format(code))
        email_thread_pool.apply_async(send_email, e, callback=callback)

    response = make_response('success')
    response.set_cookie('email', email)
    return response

@app.route("/send_again", methods=['POST'])
def send_again():
    guest_type = request.cookies.get('guest_type')
    email = request.form['email']

    if guest_type is None:
        return redirect('/')

    if email not in code_map:
        code_map[email] = make_code

    code = code_map[email]

    e = ([email], "Your Confirmation Code", 'Your code is: {}'.format(code))
    email_thread_pool.apply_async(send_email, e, callback=callback)

    response = make_response('success')
    return response

@app.route("/validate_code", methods=['POST'])
def validate_code():
    guest_type = request.cookies.get('guest_type')
    email = request.cookies.get('email')
    code = request.form['code']

    if guest_type is None:
        return redirect('/')

    if email is None:
        return redirect('/site')

    if email in hit_counter and hit_counter[email] > 3:
        print "BOI"
        return 'BLOCKED'

    if code != code_map[email]:
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

    if guest_type is None:
        return redirect('/')

    if email is None:
        return redirect('/site')

    if code != code_map[email]:
        return redirect('/site')

    if email not in email_to_rsvp:
        props = {
            'day_guest': guest_type == 'day',
            'email': email
        }

        return render_template('new_rsvp.html', **props)

    else:
        props = {
            'day_guest': guest_type == 'day',
            'email': email,
            'guests': email_to_rsvp[email]
        }

        return render_template('existing_rsvp.html', **props)

@app.route('/update_rsvp', methods=['POST'])
def update_rsvp():
    email = request.cookies.get('email')
    guests = json.loads(request.form['guests'])
    email_to_rsvp[email] = guests
    for guest in guests:
        print guest
    return 'OK'

@app.route('/sendmail')
def sendmail():
    email = (['edderick@live.co.uk'], "Cool Subject", 'Cooler body')
    email_thread_pool.apply_async(send_email, email, callback=callback)
    return 'Email sent!'

