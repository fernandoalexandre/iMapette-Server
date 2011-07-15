# !/usr/bin/env python

import datetime
import os
import logging

from django.utils import simplejson as json

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

__app_name__ = 'Le iMapette'
__author__ = 'Fernando Alexandre'

class Spot(db.Model):
    """Models an individual Spot entry."""
    latd = db.FloatProperty()
    longd = db.FloatProperty()
    accuracy = db.FloatProperty()
    altitude = db.FloatProperty()
    speed = db.FloatProperty()
    timestamp = db.IntegerProperty()
    user_id = db.StringProperty()

    # Used for Json serialization
    def to_dict(self):
        return dict([(p, unicode(getattr(self, p))) for p in self.properties()])

class User(db.Model):
    """Models a individual User. (Unique device ID)"""
    user_id = db.StringProperty()
    privacy = db.IntegerProperty()

class MainPage(webapp.RequestHandler):
    """MainPage used to serve browsers."""
    def get(self):
        spots = Spot.all()
        users = User.all()
        paths = []
        
        for user in users:
            if user.privacy == 0:
                curr = Spot.gql('WHERE user_id = :1 ORDER BY timestamp DESC', user.user_id)
                paths += [curr]
            else:
                spots.filter("user_id != ", user.user_id)

        template_values = { 'title' : __app_name__,
                            'spots' : spots,
                            'users' : users,
                            'paths' : paths}

        path = os.path.join(os.path.dirname(__file__), "index.html")
        self.response.out.write(template.render(path, template_values))

class RPCHandler(webapp.RequestHandler):
    """ Defines the methods that can be RPCed.
    NOTE: Do not allow remote callers access to private/protected "_*" methods.
    """
    
    # POST constants

    USER_ID = 'user_id'
    SPOT_COUNT = 'spotCount'
    LAT = 'latd'
    LNG = 'longd'
    ACCURACY = 'accuracy'
    ALTITUDE = 'altitude'
    SPEED = 'speed'
    TIME = 'timestamp'
    PRIVACY = 'privacy'
    
    """ Will handle the RPC GET requests."""
    def get(self):
        self.error(403) # Default Response to a empty request

    """ Will handle the RPC POST requests."""
    """ Depending on the 'method' property it will execute a different function   """
    def post(self):
        method = self.request.get('method')
        
        if method == 'addSpots':
            RPCHandler._doAddSpots(self)
        elif method == 'getSpots':
            RPCHandler._doGetSpots(self)
        elif method == 'setPrivacy':
            RPCHandler._doSetPrivacy(self)
        else:
            self.response.set_status(501) # Method not implemented
        
    def _doAddSpots(self):
        spotCount = self.request.get(RPCHandler.SPOT_COUNT)
        user_id = self.request.get(RPCHandler.USER_ID)
        
        users = User.gql("WHERE user_id= :1", user_id)
        
        if(users.count() == 0):
            user = User()
            user.user_id = user_id
            user.privacy = 0
            user.put()
        
        for i in range(int(spotCount)):
            location = Spot()
            
            location.user_id = user_id            
            location.latd = float(self.request.get('%s%d' % (RPCHandler.LAT, i)))
            location.longd = float(self.request.get('%s%d' % (RPCHandler.LNG, i)))
            location.accuracy = float(self.request.get('%s%d' % (RPCHandler.ACCURACY, i)))
            location.altitude = float(self.request.get('%s%d' % (RPCHandler.ALTITUDE, i)))
            location.speed = float(self.request.get('%s%d' % (RPCHandler.SPEED, i)))
            location.timestamp = int(self.request.get('%s%d' % (RPCHandler.TIME, i)))
            
            location.put()
        
        self.response.set_status(204) # Ok and fufilled but no info back
    
    def _doGetSpots(self):
        # Get all spots except the ones from the requesting device,
        # since he already has them locally.
        user_id = self.request.get(RPCHandler.USER_ID)
        
        if user_id == None:
            locs = Spot.all()
        else:
            locs = Spot.gql("WHERE user_id != :1", user_id)

        self.response.out.write(json.dumps([p.to_dict() for p in locs]))

        self.response.headers['Content-Type'] = 'application/json'  
        self.response.set_status(200);

    def _doSetPrivacy(self):
        user_id = self.request.get(RPCHandler.USER_ID) 
        user = User.gql("WHERE user_id = :1", user_id)
        u = user.get()
        u.privacy = int(self.request.get('%s' % RPCHandler.PRIVACY))
        u.put()
        self.response.set_status(204)


def main():
    app = webapp.WSGIApplication([
        ('/', MainPage),
        ('/rpc', RPCHandler),
        ], debug=True)
    run_wsgi_app(app)

if __name__ == "__main__":
    main()

