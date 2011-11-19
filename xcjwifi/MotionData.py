from google.appengine.ext import db

class MotionData(db.Model):
    image = db.BlobProperty(default=None)
    captured = db.DateTimeProperty(auto_now_add=False, required=True)
