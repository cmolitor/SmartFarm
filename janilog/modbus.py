import sys
import urllib
import json
import configparser
import time
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# =======================
# Functions
# =======================

def readChannels():
    # voltage phase 1 to neutral
    print("New measurement readings: ", int(time.time()))
    listValues = list()
    for c in listChannels:
        handle = client.read_holding_registers(c['register'],c['words'],unit=c['unit'])
        # print(c['description'], ":")

        if c['words'] > 1:
            decoder = BinaryPayloadDecoder.fromRegisters(handle.registers, byteorder=Endian.Big, wordorder=Endian.Big)
            value = decoder.decode_32bit_float()/float(c['factor'])
        else:
            value = handle.registers[0]/float(c['factor'])
        print(c['description'], ":", str(value))
        listValues.append(value)


# =======================
# Definitions
# =======================

print("Used Python version: ")
print(sys.version)

# Add channels
listChannels = list()
# listChannels.append({'description': "V1_ph2n", 'register': 51284, 'words': 1, 'unit': 0xFF, 'measurement': "voltage", 'factor': 100})
# listChannels.append({'description': "V2_ph2n", 'register': 51285, 'words': 1, 'unit': 0xFF, 'measurement': "voltage", 'factor': 100})
# listChannels.append({'description': "V3_ph2n", 'register': 51286, 'words': 1, 'unit': 0xFF, 'measurement': "voltage", 'factor': 100})
# listChannels.append({'description': "frequency", 'register': 51287, 'words': 1, 'unit': 0xFF, 'measurement': "frequency", 'factor': 100})
# listChannels.append({'description': "P", 'register': 50536, 'words': 2, 'unit': 0xFF, 'measurement': "activepower", 'factor': 0.1}) # factor of Socomec from value to kVA(r): 100; from kW->W: 1/1000; result: factor=0.1
# listChannels.append({'description': "P1", 'register': 50544, 'words': 2, 'unit': 0xFF, 'measurement': "activepower", 'factor': 0.1}) # factor of Socomec from value to kVA(r): 100; from kW->W: 1/1000; result: factor=0.1
# listChannels.append({'description': "P2", 'register': 50546, 'words': 2, 'unit': 0xFF, 'measurement': "activepower", 'factor': 0.1}) # factor of Socomec from value to kVA(r): 100; from kW->W: 1/1000; result: factor=0.1
# listChannels.append({'description': "P3", 'register': 50548, 'words': 2, 'unit': 0xFF, 'measurement': "activepower", 'factor': 0.1}) # factor of Socomec from value to kVA(r): 100; from kW->W: 1/1000; result: factor=0.1
# listChannels.append({'description': "Q", 'register': 50538, 'words': 2, 'unit': 0xFF, 'measurement': "reactivepower", 'factor': 0.1}) # factor of Socomec from value to kVA(r): 100; from kW->W: 1/1000; result: factor=0.1
# listChannels.append({'description': "Q1", 'register': 50550, 'words': 2, 'unit': 0xFF, 'measurement': "reactivepower", 'factor': 0.1}) # factor of Socomec from value to kVA(r): 100; from kW->W: 1/1000; result: factor=0.1
# listChannels.append({'description': "Q2", 'register': 50552, 'words': 2, 'unit': 0xFF, 'measurement': "reactivepower", 'factor': 0.1}) # factor of Socomec from value to kVA(r): 100; from kW->W: 1/1000; result: factor=0.1
# listChannels.append({'description': "Q3", 'register': 50554, 'words': 2, 'unit': 0xFF, 'measurement': "reactivepower", 'factor': 0.1}) # factor of Socomec from value to kVA(r): 100; from kW->W: 1/1000; result: factor=0.1
listChannels.append({'description': "E1", 'register': 19068, 'words': 2, 'unit': 0xFF, 'measurement': "Real energy L1..L3 consumed", 'factor': 1000}) # original unit: Wh; factor from Wh -> kWh
listChannels.append({'description': "V1_ph2n", 'register': 19000, 'words': 2, 'unit': 0xFF, 'measurement': "Voltage L1 - phase to neutral", 'factor': 1}) # original unit: Wh; factor from Wh -> kWh

# =======================
# Initialization
# =======================

# Load data from config.ini
config = configparser.ConfigParser()
config.readfp(open(r'config.ini'))

# Reading frequency in seconds
intervalTime = config.get('General', 'intervalTime')
# Load name of location or measurement title
strName = config.get('General', 'name')
# Load IP of Socomec
strIP = config.get('General', 'IPsocomec')

# print(intervalTime, strName, strIP)


# Initialize Modbus client
client = ModbusTcpClient(strIP)
ret = client.connect()
if ret:
	print("Connected to Janitza.")
else:
	print("Connection to Janitza failed.")

# Start the scheduler
sched = BlockingScheduler()

# =======================
# Main
# =======================

sched.add_job(readChannels, 'interval', seconds=int(intervalTime))
sched.start()

client.close()
