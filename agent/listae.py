#!/usr/bin/python
import getpass
import sys
import telnetlib
import time
import sqlite3
import httplib
import logging

import argparse

logging.basicConfig(level=logging.INFO)

def local_record(mac, is_new):
    if is_new:
        # Insert a row of data
        query = "insert into mac(joined, mac) values (%d,'%s')" % (
            int(time.time()), mac)
    else:
        query = "update mac set left = %d where left is null and mac = '%s'" % (
            int(time.time()), mac)
        
    cursor.execute(query)
    conn.commit()

def http_record(mac, is_new):
    httpconn = httplib.HTTPConnection(args.server, args.port)
    if is_new:
        httpconn.request("GET", "/join?macaddr=%s" % mac)
    else:
        httpconn.request("GET", "/left?macaddr=%s" % mac)
    res = httpconn.getresponse()
    if res.status != 200:
        print "Error updating: " + res.reason
    else:
        print res.read()
    httpconn.close()

def http_ping():
    httpconn = httplib.HTTPConnection(args.server, args.port)
    httpconn.request("GET", "/ping")
    res = httpconn.getresponse()
    if res.status != 200:
        print "Error updating: " + res.reason
    httpconn.close()

def fetch_current_mac():
    query = "select mac from mac where left is null"
    cursor.execute(query)
    return set([v[0] for v in cursor.fetchall()])

logging.info("Parsing arguments")
parser = argparse.ArgumentParser(description='Capture wifi data')
parser.add_argument(
    '--sqlite_filename', 
    dest='sqlite_filename', 
    default='/opt/wifi/mac.dat')
parser.add_argument(
    '--host', 
    dest='host',
    default='192.168.1.1')
parser.add_argument(
    '--user', 
    dest='user',
    default='root'
    )
parser.add_argument(
    '--password_filename', 
    dest='password_filename',
    default='/opt/wifi/router.passwd'
    )
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
    '--once', 
    dest='once',
    default=False
    )
args = parser.parse_args()
password = file(args.password_filename).readlines()[0].strip()

conn = sqlite3.connect(args.sqlite_filename)
cursor = conn.cursor()

logging.info("Creating local datastore table " + args.sqlite_filename)
try:
    cursor.execute(
        "create table mac (joined NUMERIC, left NUMERIC, mac TEXT)")
except sqlite3.OperationalError:
    pass

logging.info("Syncing local datastore %s to server %s" % (args.sqlite_filename, args.server))
mac_set = fetch_current_mac()

# make sure we're in sync...
for m in mac_set:
    http_record(m, True)

logging.info("Connecting to the server %s" % args.server)
while True:
    try:
        tn = telnetlib.Telnet(args.host)

        tn.read_until("login: ")
        tn.write(args.user + "\n")
        if password:
            tn.read_until("Password: ")
            tn.write(password + "\n")
        tn.read_until("#").split("\n")
        logging.error("Connected!")
        break
    except Exception as e:
        logging.error("Unable to connect, waiting! %s" % e)
    if args.once:
        break
    else:
        time.sleep(5)

logging.info("Fetching information from %s" % args.host)
while True:
    try:
        tn.write("wl assoclist\n")
        current_list = tn.read_until("#").split("\n")
        current_list = [i.split(" ")[1].strip() for i in current_list if i.startswith("assoclist")]
        current_set = set(current_list)
        #print "Currently connected: %d" % len(current_set)
        ping_needed = True
        for s in current_set.difference(mac_set):
            logging.info("NEW: " + s)
            local_record(s, True)
            http_record(s, True)
            ping_needed = False
        for s in mac_set.difference(current_set):
            logging.info("GONE: " + s)
            local_record(s, False)
            http_record(s, False)
            ping_needed = False
        if ping_needed:
            http_ping()
        mac_set.intersection_update(current_set)
        mac_set.update(current_set)
    except Exception as e:
        logging.error("Error recording information %s" % e)
    if args.once:
        break
    else:
        time.sleep(5)

tn.write("exit\n")
# We can also close the cursor if we are done with it
cursor.close()

