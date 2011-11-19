from google.appengine.ext import deferred
from google.appengine.api import memcache
from google.appengine.ext import db
import StringIO
import datetime

from WifiData import MacData # otherwise we get "No implementation for kind" errors

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

def invalidate_cache(full=True):
    memcache.set("last_update", datetime.datetime.now())
    if full:
        deferred.defer(update_status_cache)
  
def get_status():
    status = memcache.get("status")
    if status:
        return status + get_last_update()
    else:
        deferred.defer(update_status_cache)
        return "Unknown status: no data received by client yet (scheduled update)"

    
def update_status_cache():
    memcache.set("status", render_status())

def get_last_update():
    return "<p>Last update CST: %s</p>" % memcache.get("last_update").replace(tzinfo = GMT).astimezone(CST)
    
def render_status():
    results = db.GqlQuery("SELECT * FROM MacData WHERE left = NULL")
    output = StringIO.StringIO()
    count = results.count()
    if count:
        output.write("<h1>XinCheJian is OPENED</h1>")
        memcache.set("is_open", True);
    else:
        output.write("<h1>XinCheJian is CLOSED</h1>")
        memcache.set("is_open", False);
    output.write("<p>Currently connected: %d</p>" % count)    
    return output.getvalue()

def update_hourly_cache():
    memcache.set("hourly", render_hourly())
    
def render_hourly():
    output = StringIO.StringIO()
    results = db.GqlQuery("SELECT * FROM MacData")
    week_by_hour = [[set() for col in range(0,24)] for row in range(0,7)]
            
    for m in results:
        #output.write("<br>%s to %s (%s)" % (m.joined, m.left, m.macaddr))
        #output.write("<br>%s %s" % (m.joined.weekday(), m.joined.hour))
        joined = m.joined.replace(tzinfo = GMT).astimezone(CST)
        if m.left:
            left = m.left.replace(tzinfo = GMT).astimezone(CST)
        else:
            left = datetime.datetime.utcnow().replace(tzinfo = GMT).astimezone(CST)
        for day in range(joined.weekday(), left.weekday()+1):
            for hour in range(joined.hour, left.hour+1):
                week_by_hour[day][hour].add(m.macaddr)
    output.write("<table border=1 width=50%")
    output.write("<th>")
    output.write("<td>Hour<td>Monday<td>Tuesday<td>Wednesday<td>Thursday<td>Friday<td>Saturday<td>Sunday")
    for hour in range(0,24):
        output.write("<tr>")
        output.write("<td>%d" % hour)
        for day in range(0,7):
            output.write("<td>")
            output.write("%d" % len(week_by_hour[day][hour]))
            output.write("</td>")                
        output.write("</tr>")
    output.write("</table>")
    return output.getvalue()
