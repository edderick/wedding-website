#! /usr/local/bin/python
import sqlite3

conn = sqlite3.connect('sqlite.db')
c = conn.cursor()

try:
    c.execute('CREATE TABLE code (email, code)')
except:
    print("Can't create table code")
    pass

try:
    c.execute('CREATE TABLE rsvp ({})'.format(
        ', '.join(_guest_fields + ['email']),
    ))
except:
    print("Can't create table rsvp")
    pass

try:
    c.execute('CREATE TABLE password (password, guest_type)')
except:
    print("Can't create table password")
    pass

# INSERT INTO password vlaues ("day", "day")
# INSERT INTO password vlaues ("evening", "evening")

conn.commit()

print('Finished initializing database!')
