import sys
from pymodbus.client.sync import ModbusTcpClient
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler


def readChannels():
    # voltage phase 1 to neutral
	handle = client.read_holding_registers(51284,1,unit=0xFF)
	print "Voltage: ", handle.registers[0]/100.0

# =======================
# Initialization
# =======================

print("Used Python version: ")
print(sys.version)

# Initialize Modbus client
client = ModbusTcpClient("192.168.178.19")
ret = client.connect()
print ret

# Start the scheduler
sched = BlockingScheduler()

# Add channels
listChannels = list()

listChannels.append({'register': 51284, 'words': 1, 'unit': 0xFF, 'measurement': "voltage", 'factor': 100, 'frequency': 60})
print listChannels[0]['measurement']

# here add further channels


# read config
# check uuid
# if no uuid -> create channels
# if uuid -> get main channels (voltage, active power reactive power, frequency, )


# =======================
# Main
# =======================

sched.add_job(readChannels, 'interval', seconds=10)
sched.start()

# read_holding_registers(register address in decimal, number of words, slave to query(here: 255))
#handle = client.read_holding_registers(57616,1,unit=0xFF)
#print handle.registers[0]

client.close()

