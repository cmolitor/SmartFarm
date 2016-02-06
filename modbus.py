import sys
import urllib2
import json
import ConfigParser
import time
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
    	print channel['description'],":", channel['uuid'], int(time.time()), listValues[i]
    	# Here fire values into VZ middleware
    	addValue(channel['uuid'], int(time.time()), listValues[i])

# Add measurement value
def addValue(uuid, timestamp, value):
	url = strURL + "/data/" + uuid + ".json?operation=add&ts=" + str(timestamp) + "&value=" + str(value)
	print url
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	print jsonVZ
	return 1

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
	# print "addToGroup: " + jsonVZ
	return 1

# Get group ### Here better implement function like get all children
def getGroup(uuid):
	url = strURL + "/group/" + uuid + ".json"
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	#print "getGroup: ", jsonVZ
	return jsonVZ

# Get children of group
# Returns list with uuids of children
def getChildren(uuid):
	data = json.loads(getGroup(uuid))

	listChildren = list()
	for x in range(0,len(data['entity']['children'])):
		listChildren.append(data['entity']['children'][x]['uuid'])
	
	return listChildren

# Get title of group
def getGroupTitle(uuid):
	data = json.loads(getGroup(uuid))

	return data['entity']['title']

# Create Channel
def createChannel(type, title):
	url = strURL + "/channel.json?operation=add&type="+ type +"&title=" + title
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
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
mainGrpUUID = config.get('General', 'uuid')

if mainGrpUUID == "":
	print "no uuid"
	# create main uuid
	mainGrpUUID = createGroup(strName, 1)
	print mainGrpUUID
	config.set('General', 'uuid', mainGrpUUID)
	with open(r'config.ini', 'wb') as configfile:
		config.write(configfile)
else:
	print "Main group UUID: ", mainGrpUUID

# Check for existing subgroups
subGroups = {}
listGroups = getChildren(mainGrpUUID)

for x in listGroups:
	key = getGroupTitle(x)
	# print key, x
	if key not in subGroups:
		subGroups[key] = x
	else:
		print "Subgroup exists twice. That shouldn't happen."
		exit(500)

# print subGroups

# Now check measurement channels and to which group they belong.
# If subgroup for measurement type does not exits yet, create it.

for c in listChannels:
	strMeasurement = c['measurement']

	# Check if subgroup already exists
	if strMeasurement not in subGroups:
		_uuid = createGroup(strMeasurement, 1)
		subGroups[strMeasurement] = _uuid

	# Create channel and add to group
	if (c['measurement'] == "voltage") or (c['measurement'] == "frequency"):
		# Create channel for measurement
		_uuid = createChannel("voltage",c['description'])
		# Add channel to subgroup
		print "Added to group successully:", addToGroup(subGroups[c['measurement']], _uuid)
		# Store UUID
		c['uuid'] = _uuid
	elif (c['measurement'] == "activepower") or (c['measurement'] == "reactivepower"):
		# Create channel for measurement
		_uuid = createChannel("powersensor",c['description'])
		# Add channel to subgroup
		print "Added to group successully:", addToGroup(subGroups[c['measurement']], _uuid)
		# Store UUID
		c['uuid'] = _uuid
	else:
		print "Measurement type not known."
		exit()

# =======================
# Main
# =======================

sched.add_job(readChannels, 'interval', seconds=frequency)
sched.start()

client.close()
