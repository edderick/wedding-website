
import smtplib
from multiprocessing import Pool # Here are the big guns

def get_password():
    with open('./password.txt') as f:
	return f.readline()

def callback(arg):
    # TODO: Track failed messages?
    print arg

def send_email_job(to, subject, body):
    gmail_user = 'bethan.and.edward.wedding@gmail.com'
    gmail_password = get_password()

    sent_from = "Bethan & Edward's Wedding"

    email_text = "From: {}\nTo: {}\nSubject: {}\n\n{}".format(
	sent_from, ", ".join(to), subject, body)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(gmail_user, gmail_password)
    server.sendmail(sent_from, to, email_text)
    server.close()

email_thread_pool = Pool(processes=1)

def send_email(to, subject, body):
    print "Sending email to {} - {} - {}".format(to, subject, body)
    e = (to, subject, body)
    email_thread_pool.apply_async(send_email_job, e, callback=callback)


