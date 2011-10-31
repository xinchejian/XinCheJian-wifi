#!/usr/bin/python
import getpass
import sys
import telnetlib
import time
import sqlite3
import httplib

conn = sqlite3.connect('/opt/wifi/mac.dat')
cursor = conn.cursor()

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
    httpconn = httplib.HTTPConnection("wifi.xinchejian.com")
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
    httpconn = httplib.HTTPConnection("wifi.xinchejian.com")
    httpconn.request("GET", "/ping")
    res = httpconn.getresponse()
    if res.status != 200:
        print "Error updating: " + res.reason
    httpconn.close()

def fetch_current_mac():
    query = "select mac from mac where left is null"
    cursor.execute(query)
    return set([v[0] for v in cursor.fetchall()])

# Create table
try:
    cursor.execute(
        "create table mac (joined NUMERIC, left NUMERIC, mac TEXT)")
except sqlite3.OperationalError:
    pass

mac_set = fetch_current_mac()

# make sure we're in sync...
for m in mac_set:
    http_record(m, True)

HOST = "192.168.1.1"
user = "root"
password = file("/opt/wifi/router.passwd").readlines()[0].strip()

tn = telnetlib.Telnet(HOST)

tn.read_until("login: ")
tn.write(user + "\n")
if password:
    tn.read_until("Password: ")
    tn.write(password + "\n")
tn.read_until("#").split("\n")

while True:
    tn.write("wl assoclist\n")
    current_list = tn.read_until("#").split("\n")
    current_list = [i.split(" ")[1].strip() for i in current_list if i.startswith("assoclist")]
    current_set = set(current_list)
    #print "Currently connected: %d" % len(current_set)
    ping_needed = True
    for s in current_set.difference(mac_set):
        print "NEW: " + s
        local_record(s, True)
        http_record(s, True)
        ping_needed = False
    for s in mac_set.difference(current_set):
        print "GONE: " + s
        local_record(s, False)
        http_record(s, False)
        ping_needed = False
    if ping_needed:
        http_ping()
    mac_set.intersection_update(current_set)
    mac_set.update(current_set)
    time.sleep(5)

tn.write("exit\n")
# We can also close the cursor if we are done with it
cursor.close()
