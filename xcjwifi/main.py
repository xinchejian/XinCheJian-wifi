#!/usr/bin/env python

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import memcache

import logging
import datetime
import StringIO
import re

macaddr_validation = re.compile("([a-fA-F0-9]{2}[:|\-]?){6}")

def is_valid_mac(macaddr):
    return macaddr_validation.match(macaddr)

def invalidate_cache():
    memcache.set("last_update", datetime.datetime.now())
    memcache.set("status", None)
        
def render_status():
    results = db.GqlQuery("SELECT * FROM MacData WHERE left = NULL")
    output = StringIO.StringIO()
    count = results.count()
    if count:
        output.write("<h1>XinCheJian is OPENED</h1>")
    else:
        output.write("<h1>XinCheJian is CLOSED</h1>")
    output.write("<p>Currently connected: %d</p>" % count)
    output.write("<p>Last update GMT: %s</p>" % memcache.get("last_update"))
    return output.getvalue()

def get_status():
    status = memcache.get("status")
    if status is not None:
        return status
    else:
        status = render_status()
        if not memcache.add("status", status):
            logging.error("Memcache set failed.")
        return status

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

        
def main():
    application = webapp.WSGIApplication([('/join', JoinedHandler), ('/left', LeftHandler), ('/status', StatusHandler), ('/ping', PingHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
