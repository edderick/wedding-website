def is_legit(email):
    with open('disposable_email_blacklist.conf') as blacklist:
        blacklist_content = [line.rstrip() for line in blacklist.readlines()]
        return not email.split('@')[1] in blacklist_content

