import datetime

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


def from_cst_to_utc(d):
    return d.replace(tzinfo = CST).astimezone(GMT)

def from_utc_to_cst(d):
    return d.replace(tzinfo = GMT).astimezone(CST)