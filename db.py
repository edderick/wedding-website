import sqlite3


# --- Code table ---

def set_code_for_email(email, code):
    conn = _connect()
    c = conn.cursor()
    c.execute("INSERT INTO code VALUES (?, ?)", (email, code))
    conn.commit()


def get_code_for_email(email):
    conn = _connect()
    c = conn.cursor()

    c.execute('SELECT * FROM code WHERE email=?', (email,))

    record = c.fetchone()

    if record is None:
        return None

    return record[1]


# --- RSVP table ---

_guest_fields = [
    'firstname',
    'lastname',
    'isAttending',
    'hasDiet',
    'dietDetails',
    'needsTransport',
    'songRequest',
    'email'
]

def _record_to_guest(record):
    return dict(zip(_guest_fields, record))


def _guest_to_record(guest):
    return tuple(guest[field] for field in _guest_fields)


def set_guests(email, guests):
    conn = _connect()
    c = conn.cursor()

    c.execute('''DELETE FROM rsvp WHERE email=?''', (email,))

    sql = 'INSERT INTO rsvp ({}) VALUES ({})'.format(
        ', '.join(_guest_fields),
        ', '.join(['?'] * len(_guest_fields)))

    for guest in guests:
        c.execute(sql, _guest_to_record(guest))

    conn.commit()


def get_all_guests():
    conn = _connect()
    c = conn.cursor()

    sql = 'SELECT {} FROM rsvp'.format(','.join(_guest_fields))

    return [_record_to_guest(record) for record in c.execute(sql)]


def get_guests(email):
    conn = _connect()
    c = conn.cursor()

    sql = 'SELECT {} FROM rsvp WHERE email=?'.format(','.join(_guest_fields))

    return [_record_to_guest(record) for record in c.execute(sql, (email,))]

# --- Message table ---

def set_message(email, message):
    conn = _connect()
    c = conn.cursor()

    c.execute('DELETE FROM message WHERE email=?', (email,))
    c.execute('INSERT INTO message VALUES (?, ?)', (email, message))
    conn.commit()

def get_all_messages():
    conn = _connect()
    c = conn.cursor()

    sql = 'SELECT email, message FROM message'

    return [{
        'email': record[0],
        'message': record[1]
    } for record in c.execute(sql) if len(record[1])]

def get_message(email):
    conn = _connect()
    c = conn.cursor()

    c.execute('SELECT email, message FROM message WHERE email=?', (email,))

    record = c.fetchone()

    if record is None:
        return None

    return record[1]

# --- Password table ---

def get_guest_type_for_password(password):
    conn = _connect()
    c = conn.cursor()
    c.execute('SELECT guest_type FROM password WHERE password=?', (password,))

    record = c.fetchone()

    if record is None:
        return None

    return record[0]


def _connect():
    return sqlite3.connect('sqlite.db')
