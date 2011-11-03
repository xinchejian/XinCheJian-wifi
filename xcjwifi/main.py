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

def invalidate_cache():
    memcache.set("last_update", datetime.datetime.now())
    deferred.defer(status.update_status_cache)
  
def get_status():
    status = memcache.get("status")
    if status is not None:
        return status
    else:
        return "Unknown status!"

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

class Zone(datetime.tzinfo):
    def __init__(self,offset,isdst,name):
        self.offset = offset
        self.isdst = isdst
        self.name = name
    def utcoffset(self, dt):
        return datetime.timedelta(hours=self.offset) + self.dst(dt)
    def dst(self, dt):
            return datetime.timedelta(hours=1) if self.isdst else datetime.timedelta(0)
    def tzname(self,dt):
         return self.name

GMT = Zone(0,False,'GMT')
CST = Zone(8,False,'CST')

class HourlyHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        results = db.GqlQuery("SELECT * FROM MacData WHERE left != NULL")
        week_by_hour = [[set() for col in range(0,24)] for row in range(0,7)]
                
        for m in results:
            #self.response.out.write("<br>%s to %s (%s)" % (m.joined, m.left, m.macaddr))
            #self.response.out.write("<br>%s %s" % (m.joined.weekday(), m.joined.hour))
            joined = m.joined.replace(tzinfo = GMT).astimezone(CST)
            left = m.left.replace(tzinfo = GMT).astimezone(CST)
            for day in range(joined.weekday(), left.weekday()+1):
                for hour in range(joined.hour, left.hour+1):
                    week_by_hour[day][hour].add(m.macaddr)
        self.response.out.write("<table border=1 width=50%")
        self.response.out.write("<th>")
        self.response.out.write("<td>Hour<td>Monday<td>Tuesday<td>Wednesday<td>Thursday<td>Friday<td>Saturday<td>Sunday")
        for hour in range(0,24):
            self.response.out.write("<tr>")
            self.response.out.write("<td>%d" % hour)
            for day in range(0,7):
                self.response.out.write("<td>")
                self.response.out.write("%d" % len(week_by_hour[day][hour]))
                self.response.out.write("</td>")                
            self.response.out.write("</tr>")
        self.response.out.write("</table>")
            
def main():
    application = webapp.WSGIApplication([
        ('/join', JoinedHandler),
        ('/left', LeftHandler),
        ('/status', StatusHandler),
        ('/ping', PingHandler),
        ('/badge.gif', BadgeHandler),
        ('/button.png', ButtonHandler),
        ('/hourly', HourlyHandler),
        ],
        debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
