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
from WifiData import MacData

macaddr_validation = re.compile("([a-fA-F0-9]{2}[:|\-]?){6}")

def is_valid_mac(macaddr):
    return macaddr_validation.match(macaddr)

def get_file_content(filename):
    path = os.path.join(os.path.split(__file__)[0], filename)
    f = file(path)
    content = f.read(-1)
    return content
    
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
                status.invalidate_cache()
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
                status.invalidate_cache()
                self.response.out.write('Updated with current datetime!')
            else:
                self.response.out.write('Not currently connected')

class PingHandler(webapp.RequestHandler):
    def get(self):
        status.invalidate_cache(False)
        self.response.out.write('PONG %s' % memcache.get("last_update"))
        
class StatusHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(status.get_status())

class MachineStatusHandler(webapp.RequestHandler):
    def get(self):
        is_open = memcache.get("is_open");
        if is_open is None:
            is_open = False
        self.response.out.write("%d" % is_open)

class BadgeHandler(webapp.RequestHandler):
    def __init__(self):
        self.open_image = get_file_content('xcj_open_badge.gif')
        self.close_image = get_file_content('xcj_closed_badge.gif')
        
    def get(self):
        self.response.headers['Content-Type'] = 'image/gif'
        if memcache.get("is_open"):
            self.response.out.write(self.open_image)
        else:
            self.response.out.write(self.close_image)
            
class ButtonHandler(webapp.RequestHandler):
    def __init__(self):
        self.open_image = get_file_content('xcj_button_open.png')
        self.close_image = get_file_content('xcj_button_closed.png')
        
    def get(self):
        self.response.headers['Content-Type'] = 'image/png'
        if memcache.get("is_open"):
            self.response.out.write(self.open_image)
        else:
            self.response.out.write(self.close_image)            

class HourlyHandler(webapp.RequestHandler):
    def get(self):
        hourly = memcache.get("hourly")
        if not hourly:
            self.response.out.write("No report currently available")
        else:
            self.response.out.write(hourly)    

class HourlyUpdaterHandler(webapp.RequestHandler):
    def get(self):
        deferred.defer(status.update_hourly_cache)
        self.response.out.write("Hourly summary update scheduled")
        
def main():
    application = webapp.WSGIApplication([
        ('/join', JoinedHandler),
        ('/left', LeftHandler),
        ('/status', StatusHandler),
        ('/is_open', MachineStatusHandler),
        ('/ping', PingHandler),
        ('/badge.gif', BadgeHandler),
        ('/button.png', ButtonHandler),
        ('/hourly', HourlyHandler),
        ('/tasks/hourly', HourlyUpdaterHandler),        
        ],
        debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
