#!/usr/bin/python
import logging
import re
import httplib
import urllib
import os
import argparse

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description='Upload motion image')
parser.add_argument(
    '--server', 
    dest='server',
    default='wifi.xinchejian.com'
    )
parser.add_argument(
    '--port', 
    dest='port',
    default=80
    )
parser.add_argument(
    '--dir', 
    dest='dir',
    default='/tmp/motion'
    )
args = parser.parse_args()

r = re.compile(".*jpg")
files = [f for f in os.listdir(args.dir) if r.match(f)]
r = re.compile("[0-9]{2}-([0-9]{14})-[0-9]{2}")
data = [(f, r.match(f).group(1)) for f in files if r.match(f)] 
print data
headers = {"Content-type": "application/x-www-form-urlencoded",
           "Accept": "text/plain"}
for d in data:
  filename = args.dir + '/' + d[0]
  print "uploading %s" % filename
  httpconn = httplib.HTTPConnection(args.server, args.port)
  params = urllib.urlencode({'image': file(filename).read(), 'timestamp': d[1]})
  httpconn.request("POST", "/motion", params, headers)
  response = httpconn.getresponse()
  print response.status
  print response.read()
  if response.status == 200:
    try:
      os.remove(filename)
    except:
      pass
