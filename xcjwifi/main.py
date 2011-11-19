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
from MotionData import MotionData
import time_utils

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

class MotionHandler(webapp.RequestHandler):
    def post(self):
        image = self.request.get('image')
        ts = self.request.get('timestamp')
        self.response.out.write(ts)

        ts_datetime = datetime.datetime(int(ts[0:4]),int(ts[4:6]),int(ts[6:8]),int(ts[8:10]),int(ts[10:12]), int(ts[12:14]))
        self.response.out.write(ts_datetime)
        self.response.out.write("<br>%d" % len(self.request.str_POST['image']))
        utc_ts = time_utils.from_cst_to_utc(ts_datetime)

        results = db.GqlQuery("SELECT * FROM MotionData WHERE captured = DATETIME('%s')" % utc_ts.strftime('%Y-%m-%d %H:%M:%S'))
        if results.count() > 0:
            self.response.out.write("<br>Error! entry for %s already exist!" % utc_ts)
        else:
            m = MotionData(image=self.request.str_POST['image'], captured = utc_ts)
            m.put()


class MotionShowHandler(webapp.RequestHandler):
    def get(self):
        results = db.GqlQuery("SELECT * FROM MotionData ORDER BY captured DESC LIMIT 1")
        self.response.headers['Content-Type'] = 'image/jpeg'
        #self.response.out.write('%d<br>' % results.count(1))
        if results.count() > 0:
            self.response.out.write(results.get().image)
        #else:
        #    self.response.out.write("Error, no image recorded yet")
            
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
        ('/motion', MotionHandler),
        ('/show', MotionShowHandler),
        ],
        debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
