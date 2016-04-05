import urllib2
import json

# Deleting a channel from vz database
# first the user vz@localhost needs the proper permissions. 
# For this execute: (grant delete on volkszaehler.* to 'vz'@'localhost';) on the mysql console after loging in as root
# url = 'http://127.0.0.1/vz/htdocs/middleware.php/channel/__uuid___.json?operation=delete'

listChannels = list()

def addChannel(type="power", resolution="2000", title="testMetec"):
	url = "http://127.0.0.1/vz/htdocs/middleware.php/channel.json?operation=add&type="+ type +"&resolution=" + resolution + "&title=" + title
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	data = json.loads(jsonVZ)
	_uuid = data["entity"]["uuid"]
	return _uuid

def delChannel(uuid):
	# Deleting a channel from vz database
	# first the user vz@localhost needs the proper permissions. 
	# For this execute: (grant delete on volkszaehler.* to 'vz'@'localhost';) on the mysql console after loging in as root
	url = "http://127.0.0.1/vz/htdocs/middleware.php/channel/"+ uuid + ".json?operation=delete"
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	print(jsonVZ)

def createGroup(title="newGroup", public=1):
	url = "http://127.0.0.1/vz/htdocs/middleware.php/group.json?operation=add&title=" + title + "&public=" + str(public)
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	# print(jsonVZ)
	data = json.loads(jsonVZ)
	_uuid = data["entity"]["uuid"]
	return _uuid

def getGroup(uuid):
	url = "http://127.0.0.1/vz/htdocs/middleware.php/group/" + uuid + ".json"
	# url = "http://127.0.0.1/vz/htdocs/middleware.php/group/" + uuid + ".json"
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	print(jsonVZ)
	return 1
	data = json.loads(jsonVZ)
	_uuid = data["entity"]["uuid"]
	return _uuid

# funktioniert nicht
def getGroupByTitle(title):
	url = "http://127.0.0.1/vz/htdocs/middleware.php/group.json?title=" + title
	# url = "http://127.0.0.1/vz/htdocs/middleware.php/group/" + uuid + ".json"
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	print(jsonVZ)
	return 1
	data = json.loads(jsonVZ)
	_uuid = data["entity"]["uuid"]
	return _uuid

def getPublicChannels():
	url = "http://127.0.0.1/vz/htdocs/middleware.php/channel.json"
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	print(jsonVZ)
	return 1

def getPublicGroups():
	url = "http://127.0.0.1/vz/htdocs/middleware.php/group.json"
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	print(jsonVZ)
	return 1

	
def addToGroup(uuidGroup, uuidChannel):
	url = "http://127.0.0.1/vz/htdocs/middleware.php/group/" + uuidGroup + ".json?operation=add&uuid=" + uuidChannel
	req = urllib2.Request(url)
	response = urllib2.urlopen(req)
	jsonVZ = response.read()
	print(jsonVZ)
	return 1

# _uuid = addChannel()
_uuid = createGroup()
# _uuid = getGroups()

#_uuid = addToGroup("36d00240-7f08-11e4-8600-c5689991ddf9", "70c93240-7e32-11e4-a414-11f1d4c86a2c")
#_uuid = getGroup("36d00240-7f08-11e4-8600-c5689991ddf9")
# _uuid = getGroupByTitle("newGroup")
#getPublicChannels()
getPublicGroups()
#print _uuid

#listChannels.append(_uuid)

#for c in xrange(len(listChannels)):
#	print(_uuid)

#delChannel(_uuid)


