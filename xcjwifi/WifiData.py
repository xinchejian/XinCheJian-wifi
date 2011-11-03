from google.appengine.ext import db

class MacData(db.Model):
    macaddr = db.StringProperty(multiline=False)
    joined = db.DateTimeProperty(auto_now_add=True)
    left = db.DateTimeProperty(auto_now_add=False)