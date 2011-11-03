from google.appengine.api import memcache
from google.appengine.ext import db
import StringIO

def update_status_cache():
    memcache.set("status", render_status())

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
    output.write("<p>Last update GMT: %s</p>" % memcache.get("last_update"))
    return output.getvalue()