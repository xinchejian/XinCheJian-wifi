#!/usr/bin/env python

from google.appengine.ext import deferred
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import memcache

import os
import logging
import datetime
import re
import status

macaddr_validation = re.compile("([a-fA-F0-9]{2}[:|\-]?){6}")

def is_valid_mac(macaddr):
    return macaddr_validation.match(macaddr)

def invalidate_cache():
    memcache.set("last_update", datetime.datetime.now())
    deferred.defer(status.update_status_cache)
  
def get_status():
    status = memcache.get("status")
    if status is not None:
        return status
    else:
        return "Unknown status!"

class MacData(db.Model):
    macaddr = db.StringProperty(multiline=False)
    joined = db.DateTimeProperty(auto_now_add=True)
    left = db.DateTimeProperty(auto_now_add=False)

class JoinedHandler(webapp.RequestHandler):
    def get(self):
        macaddr = self.request.get('macaddr')
        if not is_valid_mac(macaddr):
            self.response.out.write('Invalid macaddr!')            
        else:
            results = db.GqlQuery("SELECT * FROM MacData WHERE macaddr = :1 AND left = NULL", macaddr)
            if results.count(1):
                self.response.out.write("Already connected")
            else:
                m = MacData(macaddr=macaddr)
                m.put()
                invalidate_cache()
                self.response.out.write('New connection recorded!')

class LeftHandler(webapp.RequestHandler):
    def get(self):
        macaddr = self.request.get('macaddr')
        if not is_valid_mac(macaddr):
            self.response.out.write('Invalid macaddr!')            
        else:
            results = db.GqlQuery("SELECT * FROM MacData WHERE macaddr = :1 AND left = NULL", macaddr)
            if results.count(1):
                macdata = results.get()
                macdata.left = datetime.datetime.now()
                macdata.put()
                invalidate_cache()
                self.response.out.write('Updated with current datetime!')
            else:
                self.response.out.write('Not currently connected')

class PingHandler(webapp.RequestHandler):
    def get(self):
        invalidate_cache()
        self.response.out.write('PONG %s' % memcache.get("last_update"))
        
class StatusHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(get_status())

class BadgeHandler(webapp.RequestHandler):
    def __init__(self):
        open_path = os.path.join(os.path.split(__file__)[0], 'xcj_open_badge.gif')
        close_path = os.path.join(os.path.split(__file__)[0], 'xcj_closed_badge.gif')
        self.open_image = file(open_path).read();
        self.close_image = file(close_path).read();
        
    def get(self):
        self.response.headers['Content-Type'] = 'image/gif'
        if memcache.get("is_open"):
            self.response.out.write(self.open_image)
        else:
            self.response.out.write(self.close_image)
        
def main():
    application = webapp.WSGIApplication([
        ('/join', JoinedHandler),
        ('/left', LeftHandler),
        ('/status', StatusHandler),
        ('/ping', PingHandler),
        ('/badge.gif', BadgeHandler)
        ],
        debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
