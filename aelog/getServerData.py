from xml.etree import ElementTree
from io import BytesIO
import csv
import time
import requests
import datetime
import configparser

# =======================
# Description
# =======================
'''
This script allows to read historical data from aesitelink.

In order to use the script follow these steps:
1) Rename tmpl-config.ini in config.ini
2) Fill in your credentials in config.ini
3) Place config.ini and this file (getServerData.py) in the same folder
4) Execute with python3 getServerData.py
5) Wait..
6) The script creates a file for each inverter in the plant
'''

# Requesting plant information and inverter list
def getInverters(user, password, plant):
	xmlInfo = "<?xml version='1.0' encoding='utf-8'?>"
	authData = "<Auth><Username>" + user + "</Username><Password>" + password + "</Password></Auth>"
	command = "<GetInverterList><Plant>" + plant + "</Plant></GetInverterList>"
	xmlString = xmlInfo + "<rws_request>" + authData + command + "</rws_request>"
	url = "http://ds.aesitelink.de/DataServiceApi.asmx/GetInverterList"

	headers = {'host': 'ds.aesitelink.de'}
	payload = {'xmlData': xmlString}

	r = requests.post(url, data=payload, headers=headers)

	# Parse xml tree
	tree = ElementTree.parse(BytesIO(r.content))
	root = tree.getroot()

	# Parse inner xml tree. It seems there are two trees nested. The second has to be read with .text otherwise there are reading errors
	response = ElementTree.fromstring(root.text)

	plant = response.find('Plant')

	# Iteriere über alle Inverter-Elemente
	listInverters = list()
	print("Seriennummer \t  Name \t \t    ID")
	for xy in plant.findall('Inverter'):
		print(xy.get('serial'), " ", xy.get('name'), " ", xy.get('id'))
		listInverters.append({'serial': xy.get('serial'), 'name': xy.get('name'), 'id': xy.get('id')})

	return listInverters

# Get the inverter data - 10 minutes time interval
def getInverterData10min(user, password, inverterSerial, inverterID, fromTime, toTime):
	filename = "10min" + inverterSerial + "_" + datetime.datetime.fromtimestamp(int(fromTime)).strftime('%Y-%m-%d') + "_" + datetime.datetime.fromtimestamp(int(toTime)).strftime('%Y-%m-%d') + ".csv"
	myfile = open(filename, 'a')
	wr = csv.writer(myfile)  #,quoting=csv.QUOTE_ALL

	for step in range(fromTime,toTime,86400):
		_fromTime = step
		_toTime = step + 86400
		print("Lese Daten von Tag: ", datetime.datetime.fromtimestamp(int(step)).strftime('%Y-%m-%d'))

		# Compose message to request data from server
		xmlInfo = "<?xml version='1.0' encoding='utf-8'?>"
		authData = "<Auth><Username>" + user + "</Username><Password>" + password + "</Password></Auth>"
		command = "<GetInverterData><InverterId>" + inverterID + "</InverterId> <FromDate>" + str(_fromTime) + "</FromDate> <ToDate>" + str(_toTime) + "</ToDate></GetInverterData>"
		xmlString = xmlInfo + "<rws_request>" + authData + command + "</rws_request>"
		url = "http://ds.aesitelink.de/DataServiceApi.asmx/GetInverterData"

		headers = {'host': 'ds.aesitelink.de'}
		payload = {'xmlData': xmlString}

		r = requests.post(url, data=payload, headers=headers)

		# print(r.content)

		# Parse xml tree
		tree = ElementTree.parse(BytesIO(r.content))
		root = tree.getroot()
		# print(root.text)

		# Parse inner xml tree. It seems there are two trees nested. The second has to be read with .text otherwise there are reading errors
		response = ElementTree.fromstring(root.text)

		InverterData = response.find('InverterData')

		if int(InverterData.get("RecordsLeft"))!=0:
			print("Something unexpected happened. Contact the author.")

		values = list()
		for Data in InverterData.findall('Data'):
			dataset = list()
			dataset.append(Data.get("Time"))
			_fromTime = int(Data.get("Time"))

			_utc_offset = datetime.datetime.fromtimestamp(_fromTime) - datetime.datetime.utcfromtimestamp(_fromTime)
			_date = datetime.datetime.fromtimestamp(_fromTime-_utc_offset.total_seconds()).strftime('%Y-%m-%d %H:%M:%S')

			dataset.append(_date)		

			# Iteriere über alle Inverter-Elemente
			for xy in Data.findall('p'):
				dataset.append(float(xy.text)/(10**int(xy.get("dec"))))
			values.append(dataset)


		for x in values:
			wr.writerow(x)

		time.sleep(5) # Time limit of server between two requests


# get data in other intervals
def getInverterDataInterval(user, password, inverterSerial, inverterID, fromTime, toTime, interval):
	if interval == "Month":
		_type = "Daily_"
		step = 86400 * 100  # server delivers only 100 data points at once, thus 100 days
		timeformat = '%Y-%m-%d'
	elif interval == "Year":
		_type = "Monthly_"
		step = 86400 * 365  # server delivers only 100 data points at once. ok we will read only 12 months (datapoints) at once
		timeformat = '%Y-%m'
	elif interval == "Overall":
		_type = "Yearly_"
		step = 86400 * 365 * 20  # server delivers only 100 data points at once. ok we will read only 20 years (datapoints) at once
		timeformat = '%Y'
	else:
		print("Something went wrong.")
		exit()

	filename = _type + inverterSerial + "_" + datetime.datetime.fromtimestamp(int(fromTime)).strftime('%Y-%m-%d') + "_" + datetime.datetime.fromtimestamp(int(toTime)).strftime('%Y-%m-%d') + ".csv"
	myfile = open(filename, 'a')
	wr = csv.writer(myfile)  #,quoting=csv.QUOTE_ALL

	for _time in range(int(fromTime),int(toTime),step):
		print("Lese Daten ab: ", datetime.datetime.fromtimestamp(int(_time)).strftime(timeformat))

		xmlInfo = "<?xml version='1.0' encoding='utf-8'?>"
		authData = "<Auth><Username>" + user + "</Username><Password>" + password + "</Password></Auth>"
		command = "<GetObjectDataForInterval><ObjectId>" + inverterID + "</ObjectId><ObjectType>Inverter</ObjectType><DataType>Energy</DataType><IntervalType>" + interval + "</IntervalType><FromDate>" + str(_time) + "</FromDate><ToDate>" + str(_time + step) + "</ToDate></GetObjectDataForInterval>"
		xmlString = xmlInfo + "<rws_request>" + authData + command + "</rws_request>"
		url = "http://ds.aesitelink.de/DataServiceApi.asmx/GetObjectDataForInterval"

		headers = {'host': 'ds.aesitelink.de'}
		payload = {'xmlData': xmlString}

		r = requests.post(url, data=payload, headers=headers)
		# print(r.content)

		# Parse xml tree
		tree = ElementTree.parse(BytesIO(r.content))
		root = tree.getroot()
		# print(root.text)

		# Parse inner xml tree. It seems there are two trees nested. The second has to be read with .text otherwise there are reading errors
		response = ElementTree.fromstring(root.text)

		for Data in response.findall('d'):
			if Data == None:
				print("Something strange happened. Contact author.")

			dataset = list()
			_fromTime = int(Data.get("t"))

			_utc_offset = datetime.datetime.fromtimestamp(_fromTime) - datetime.datetime.utcfromtimestamp(_fromTime)
			_date = datetime.datetime.fromtimestamp(_fromTime-_utc_offset.total_seconds()).strftime(timeformat)

			# print(Data.get("t"), _date, Data.text)
			dataset.append(Data.get("t"))		
			dataset.append(_date)		
			dataset.append(Data.text)	

			wr.writerow(dataset)

		time.sleep(5) # Time limit of server between two requests

# =======================
# Initialization
# =======================
if __name__ == "__main__":
	# Load data from config.ini
	config = configparser.ConfigParser()
	config.readfp(open(r'config.ini'))

	# Reading general data
	user = config.get('General', 'user')
	password = config.get('General', 'password')
	plant = config.get('General', 'plant')

	# Reading time information 
	fromTime = int(config.get('Time', 'starttime'))
	toTime = int(config.get('Time', 'endtime'))

	# =======================
	# Reading data
	# =======================

	# get inverters of plant
	listInverters = list()
	listInverters = getInverters(user, password, plant)
	#exit()
	time.sleep(5) # Time limit of server between two requests

	# get data of list of inverters if list exists
	if listInverters:
		for inverter in listInverters:
			print("Lese Daten von Wechselrichter mit Seriennummer: ", inverter['serial'], " ID:", inverter['id'])
			inverterSerial = inverter['serial']
			inverterID = inverter['id']

			# Different function calls to download data with different resolution. Comment out if needed.
			getInverterData10min(user, password, inverterSerial, inverterID, fromTime, toTime)
			getInverterDataInterval(user, password, inverterSerial, inverterID, fromTime, toTime, "Month")
			getInverterDataInterval(user, password, inverterSerial, inverterID, fromTime, toTime, "Year")
			getInverterDataInterval(user, password, inverterSerial, inverterID, fromTime, toTime, "Overall")
	else: # define serial and ID manually for single inverter
		inverterSerial = "LBAN02261010670"
		inverterID = "61591"
		print("Lese Daten von Wechselrichter mit Seriennummer: ", inverterSerial, " ID:", inverterID)
		getInverterDataInterval(user, password, inverterSerial, inverterID, "1420070400", "1422748800", "Month")
		getInverterDataInterval(user, password, inverterSerial, inverterID, "1420070400", "1422748800", "Year")
		getInverterDataInterval(user, password, inverterSerial, inverterID, "1420070400", "1422748800", "Overall")

