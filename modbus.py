import sys
import urllib2
import json
import ConfigParser
from pymodbus.client.sync import ModbusTcpClient
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# =======================
# Functions
# =======================

def readChannels():
    # voltage phase 1 to neutral
    listValues = list()
    for c in listChannels:
    	handle = client.read_holding_registers(c['register'],c['words'],unit=c['unit'])
    	listValues.append(handle.registers[0]/float(c['factor']))
    	#print c['description'],":", handle.registers[0]/float(c['factor'])

    for i, channel in enumerate(listChannels):
    	print channel['description'],":", listValues[i]
    	# Here fire values into VZ middleware

# Create group in VZ
def createGroup(title="Molitor", public=1):
	url = strURL + "/group.json?operation=add&title=" + title + "&public=" + str(public)
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	# print(jsonVZ)
	data = json.loads(jsonVZ)
	_uuid = data["entity"]["uuid"]
	return _uuid

# Add group or channel to a parent group
def addToGroup(uuidParent, uuidChild):
	url = strURL + "/group/" + uuidParent + ".json?operation=add&uuid=" + uuidChild
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	print "addToGroup: " + jsonVZ
	return 1

# Get group ### Here better implement function like get all children
def getGroup(uuid):
	url = strURL + "/group/" + uuid + ".json"
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	print "getGroup: ", jsonVZ
	return 1
	data = json.loads(jsonVZ)
	_uuid = data["entity"]["uuid"]
	return _uuid

# =======================
# Definitions
# =======================

# Reading frequency in seconds
frequency = 5

# Add channels
listChannels = list()
listChannels.append({'description': "V1_ph2n", 'register': 51284, 'words': 1, 'unit': 0xFF, 'measurement': "voltage", 'factor': 100})
#listChannels.append({'description': "V2_ph2n", 'register': 51285, 'words': 1, 'unit': 0xFF, 'measurement': "voltage", 'factor': 100})
#listChannels.append({'description': "V3_ph2n", 'register': 51286, 'words': 1, 'unit': 0xFF, 'measurement': "voltage", 'factor': 100})
#listChannels.append({'description': "frequency", 'register': 51287, 'words': 1, 'unit': 0xFF, 'measurement': "frequency", 'factor': 100})
#listChannels.append({'description': "P1", 'register': 51296, 'words': 1, 'unit': 0xFF, 'measurement': "activepower", 'factor': 100})
#listChannels.append({'description': "P2", 'register': 51297, 'words': 1, 'unit': 0xFF, 'measurement': "activepower", 'factor': 100})
#listChannels.append({'description': "P3", 'register': 51298, 'words': 1, 'unit': 0xFF, 'measurement': "activepower", 'factor': 100})
#listChannels.append({'description': "Q1", 'register': 51299, 'words': 1, 'unit': 0xFF, 'measurement': "reactivepower", 'factor': 100})
#listChannels.append({'description': "Q2", 'register': 51300, 'words': 1, 'unit': 0xFF, 'measurement': "reactivepower", 'factor': 100})
#listChannels.append({'description': "Q3", 'register': 51301, 'words': 1, 'unit': 0xFF, 'measurement': "reactivepower", 'factor': 100})

strURL = "http://192.168.178.45/vz/htdocs/middleware.php"
strName = "Molitor"
# =======================
# Initialization
# =======================

print("Used Python version: ")
print(sys.version)

# Initialize Modbus client
client = ModbusTcpClient("192.168.178.19")
ret = client.connect()
if ret:
	print "Connected."
else:
	print "Connection failed."
	exit()

# Start the scheduler
sched = BlockingScheduler()

# Parse config file and check if already a main uuid has been created. If not: create one (initial start of program)
config = ConfigParser.ConfigParser()
config.readfp(open(r'config.ini'))
uuid = config.get('General', 'uuid')

if uuid == "":
	print "no uuid"
	# create main uuid
	uuid = createGroup(strName, 1)
	print uuid
	config.set('General', 'uuid', uuid)
	with open(r'config.ini', 'wb') as configfile:
		config.write(configfile)
else:
	print uuid

# Loop over channels and check for required sub uuids (e.g. power)
uuids = {}

for c in listChannels:
	print c['measurement']
	uuids[c['measurement']] = createGroup(c['measurement'], 1)
	print uuids
	addToGroup(uuid, uuids[c['measurement']])

# create channel uuid for channel
# if sub uuid not available create sub group 
# add channel to sub group

# =======================
# Main
# =======================

sched.add_job(readChannels, 'interval', seconds=frequency)
sched.start()

client.close()
