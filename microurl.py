import os
import json
import sys
import time

from flask import abort, Flask, redirect, render_template, request,\
                  send_from_directory
from validators import domain as domaincheck
from validators import ipv4 as ipcheck
from validators import url as urlcheck

import database
import database_cleaner
import random_micro


#FLASK#########################################################################
app = Flask(__name__)   # Instantiate a flask app.

db = database.DB_Interface()


@app.route('/')
def route_index():
    '''
        Main index page handler.
    '''
    return render_template('index.html')


@app.route('/about')
def route_about():
    '''
        About page handler.
    '''
    return render_template('about.html')


@app.route('/top')
def route_top():
    '''
        All registered micros page handler.
    '''
    return render_template('top.html', registry=read_top())

@app.route('/recent')
def route_recent():
    '''
        All registered micros page handler.
    '''
    return render_template('recent.html', registry=read_recent())


@app.route('/generate_micro', methods=['POST'])
def route_generate_micro():
    '''
        Generate micro POST request handler.
    '''
    data = parse_form_data(request.form)
    url = data['url'].strip()
    micro = get_micro(url)

    if not micro:
        micro = generate_micro()

        # Store the micro and URL in the database.
        register_micro(micro, url, data['public'])

    return json.dumps({"status": "OK", "micro": micro, "error": ""})


@app.route('/<micro>')
def route_micro(micro):
    '''
        Micro to real URL redirection handler.
    '''
    try:
        temp = lookup_micro(micro)

        if urlcheck(temp):
            return redirect(temp)
        elif domaincheck(temp):
            return redirect("http://" + temp)
        elif ipcheck(temp.split(':')[0]) and urlcheck('http://' + temp):
            # checks for plain ip or an ip with something after it
            return redirect("http://" + temp)
        else:
            abort(404)
    except Exception as e:
        # If micro is not registered, handle the exception from trying to look
        # it up and raise a 404 HTTP error.
        sys.stderr.write(str(e))
        abort(404)


@app.errorhandler(404)
def route_404(error):
    '''
        Generate a 404 page.
    '''
    return 'invalid url'


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico')


#BUSINESS LOGIC################################################################
def parse_form_data(form_data):
    '''
        Get form_data as a dict.
    '''
    try:
        if form_data['public'] == 'on':
            public = True
    except KeyError:
        public = False

    url = form_data['url']

    return {'url': url, 'public': public}


def generate_micro():
    '''
        Generates a random MICRO_LEN length ASCII code.
    '''
    return random_micro.random_words(3)


def lookup_micro(micro):
    '''
        Returns micro's associated url.
    '''
    try:
        data = read_data(micro)
        increment_hit(micro)
        return data
    except KeyError as e:
        raise e

def get_micro(url):
    '''
        Check if the url already exists.
    '''
    with db:
        result = db.query_real_link(url)
        if result:
            return result[0]
        return None


def register_micro(micro, url, public):
    '''
        Stores a micro and URL pair in the database.
    '''
    DAY_SECS = 24 * 60 * 60

    with db:
        tnow = int(time.time())
        rc = db.insert(micro, url, tnow, tnow + DAY_SECS, public)


def read_top():
    '''
        Read all data from DB and return as dict.
    '''
    with db:
        data = db.get_top()

    if not(data):
        return {'': 'nothing here'}
    else:
        return {d[1] : d[2] for d in data}


def read_recent():
    '''
        Read all data from DB and return as dict.
    '''
    with db:
        data = db.get_recent()

    if not(data):
        return {'': 'nothing here'}
    else:
        return {d[1] : d[2] for d in data}


def read_data(query):
    '''
        Search for and return a query in the DB otherwise raise Exception.
    '''
    with db:
        data = db.query_micro_link(query)

    if not(data):
        raise KeyError('{} not found in database'.format(query))
    else:
        return data[2]


def increment_hit(query):
    with db:
        db.increment_hit(query)


def remove_expired():
    '''
        Clear expired links from databased.
    '''
    print('Clearing expired links.')
    with db:
        db.clear_expired()


database_cleaner.start(remove_expired)
