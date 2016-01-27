import sys
from pymodbus.client.sync import ModbusTcpClient

print("Used Python version: ")
print(sys.version)

# Modbus client
client = ModbusTcpClient("192.168.178.19")
ret = client.connect()

print ret

# read_holding_registers(register address in decimal, number of words, slave to query(here: 255))
handle = client.read_holding_registers(57616,1,unit=0xFF)

print handle.registers[0]

client.close()
