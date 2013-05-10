#!/usr/bin/python

from maproulette import app, models
from flask_oauth import OAuth
from flask import request, url_for, redirect, session
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

# instantite OAuth object
oauth = OAuth()
osm = oauth.remote_app(
    'osm',
    base_url = app.config['OSM_URL'] + 'api/0.6/',
    request_token_url = app.config['OSM_URL'] + 'oauth/request_token',
    access_token_url = app.config['OSM_URL'] + 'oauth/access_token',
    authorize_url = app.config['OSM_URL'] + 'oauth/authorize',
    consumer_key = app.config['OAUTH_KEY'],
    consumer_secret = app.config['OAUTH_SECRET']
)

@osm.tokengetter
def get_osm_token(token=None):
    session.regenerate()
    return session.get('osm_token')

@app.route('/oauth/authorize')
def oauth_authorize():
    """Initiates OAuth authorization agains the OSM server"""
    return osm.authorize(callback=url_for('oauth_authorized',
      next=request.args.get('next') or request.referrer or None))

@app.route('/oauth/callback')
@osm.authorized_handler
def oauth_authorized(resp):
    """Receives the OAuth callback from OSM"""
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        return redirect(next_url)
    session['osm_token'] = (
      resp['oauth_token'],
      resp['oauth_token_secret']
    )
    data = osm.get('user/details').data
    app.logger.debug("Getting user data from osm")
    if not data:
        return False
    else:
        userxml = data.find('user')
        osmid = userxml.attrib['id']
        # query for existing user
        if bool(models.OSMUser.query.filter(models.OSMUser.id==osmid).count()):
            #user exists
            user = OSMUser.query.filter(OSMUser.id==osmid).first()
            print('user found')
        else:
            # create new user
            user = models.OSMUser()
            user.id = osmid
            user.display_name = userxml.attrib['display_name']
            homexml = userxml.find('home')
            if homexml is not None:
                user.home_location = 'POINT(%s %s)' % (homexml.attrib['lon'], homexml.attrib['lat'])
            else:
                print('no home for this user')
            db.session.add(user)
            db.session.commit()
            print('user created')
    session['display_name'] = user.display_name
    session['osm_id'] = user.id
    return redirect(next_url)
