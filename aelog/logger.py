import socket
import sys
import struct
import time
import email
import xml.etree.ElementTree as ET
from io import BytesIO
from io import StringIO


"""
Programm zum Empfangen von Daten von Refusol/Sinvert/AdvancedEnergy Wechselrichter
Getestet mit einem Sinvert PVM20 und einem RaspberryPi B

Einstellungen im Wechselrichter:
IP: Freie IP-Adresse im lokalen Netzwer
Netmask: 255.255.255.0
Gateway: IP-Adresse des Rechners auf dessen dieses Prg läuft(zb. Raspberry),

Einstellungen am Rechner(zb. Raspberry)
routing aktivieren nach jedem Neustart:
sudo sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'
oder einmailig:
sudo nano /etc/sysctl.conf 
und for "net.ipv4.ip_forward=1" # entfernen; d.h. reinkommentieren

Pakete welche an die IP des Logportals gehen and die IP des Raspi umleiten
sudo iptables -t nat -A PREROUTING -d 88.79.234.30 -j DNAT --to-destination ip.des.rasp.berry
sudo iptables -t nat -A PREROUTING -d 195.27.237.106 -j DNAT --to-destination 192.168.0.212

Pakete als absender die IP des Raspi eintragen
sudo iptables -t nat -A POSTROUTING -j MASQUERADE

Damit dies auch nach einem Neustart funktioniert auch in die crontab eintragen:
sudo crontab -e
@reboot sudo iptables -t nat -A PREROUTING -d 88.79.234.30 -j DNAT --to-destination ip.des.rasp.berry; sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo crontab -e
@reboot sudo iptables -t nat -A PREROUTING -d 195.27.237.106 -j DNAT --to-destination 192.168.0.212; sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE


Start des Programms via Kommandozeile:
sudo python3 nameDerDatei.py

"""

class Request:
	def __init__(self, request):
		stream = StringIO(request)
		request = stream.readline()

		words = request.split()
		[self.command, self.path, self.version] = words

		self.headers = email.message_from_string(request)
		self.content = stream.read()

	def __getitem__(self, key):
		return self.headers.get(key, '')

def byteorder():
	return sys.byteorder

def standard_encoding():
	return sys.getdefaultencoding()

def standardausgabe_encoding():
	return sys.stdout.encoding

def string2bytes(text):
	return bytes(text, "utf8")

def bytes2string(bytes):
	return str(bytes, "utf8")

def converthex2float(hexval):
	#print(hexval)
	try:
		return round(struct.unpack('>f', struct.pack('>I', int(float.fromhex(hexval))))[0],2)
	except BaseException as e:
		print(str(e) + '\r\n')
		return 0

def converthex2int(hexval):
	#print(hexval)
	try:
		return struct.unpack('>i', struct.pack('>I', int(float.fromhex(hexval))))[0]
	except BaseException as e:
		print(str(e) + '\r\n')
		return 0

def convertHex2SignedInt16bit(_hex):
	x = int(_hex, 16)
	# check sign bit
	if (x & 0x8000) == 0x8000:
		# if set, invert and add one to get the negative value, then add the negative sign
		x = -( (x ^ 0xffff) + 1)

	return x

def send2portal(addr,port,data):
    #Sende zu Sitelink/Refu-Log Portal
    server_addr = (addr, port)
    print(server_addr)
    try:
      client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      client_socket.settimeout(5)
      client_socket.connect(server_addr)
      sendcontent = data[data.find('xmlData'):]
      senddata = ('POST /InverterService/InverterService.asmx/CollectInverterData HTTP/1.1\r\n'
                  +'Host: ' + addr + '\r\n'
                  +'Content-Type: application/x-www-form-urlencoded\r\n'
                  +'Content-Length: ' + str(len(sendcontent)) + '\r\n'
                  +'\r\n'
                  + sendcontent)
      print('Senddata: ' + senddata)
      client_socket.send(string2bytes(senddata))#Sende empfangene Daten von WR zu Portal
      daten = client_socket.recv(1024)#Empfange Rückmeldung von Portal
      datenstring = bytes2string(daten)
      print(datenstring)
    except BaseException as e:
      print(str(e) + '\r\n')
    client_socket.close()
    del client_socket

def getokmsg():
	return ('HTTP/1.1 200 OK'
	+'Cache-Control: private, max-age=0'
	+'Content-Type: text/xml; charset=utf-8\r\n'
	+'Content-Length: 83\r\n'
	+'\r\n'
	+'<?xml version="1.0" encoding="utf-8"?>'
	+'<string xmlns="InverterService">OK</string>\r\n')

# =======================
# Main-function
# =======================
def main():
	global server_socket
	#Init TCP-Server
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	#Server binden mit der IP des Raspi
	#server_socket.bind((socket.gethostbyname(socket.gethostname()), 80))
	#Raspi muss eine fixe IP haben!
	server_socket.bind(('192.168.0.212', 80))

	while True:
		print('Listening for data...')
		rcdvMessageString = ''
		rcdvMessageBytes = string2bytes('')
		server_socket.listen(5) # Socket beobachten
		client_serving_socket, addr = server_socket.accept()
		while True:
			rcvbytes = client_serving_socket.recv(1024) # Daten empfangen

			rcdvMessageString = rcdvMessageString + bytes2string(rcvbytes)
			rcvok = rcdvMessageString.find('xmlData')
			# print(rcvok)
			if rcvok >= 0:#Solange Daten lesen, bis xmlData empfangen wurden
				rcdvMessageBytes = rcdvMessageBytes+rcvbytes
				break
			else:
				rcdvMessageBytes = rcdvMessageBytes+rcvbytes

		# Create HTTP Request object
		print("================= Begin HTTP object =================")
		r = Request(bytes2string(rcdvMessageBytes))
		print(r.command)
		print(r.path)
		print(r.version)

		# for header in r.headers:
		# 	print(header, r[header])

		print("r.content: ", r.content)

		if r.content.find("xmlData")>=0:
		    data = r.content[8:] # remove: "xmldata=""
		    print(data)

		    tree = ET.ElementTree(ET.fromstring(data))
		    root = tree.getroot()
		    print("root: ", root)

		    # Iterate all p-Elements
		    # for xy in root.find('d').findall('p'):
		    #     _type = dicP[xy.get('i')]['type']  # Lese Typ aus Dictionary
		    #     _factor = dicP[xy.get('i')]['factor']  # Lese Faktor aus Dictionary
		    #     _valueHex = xy.text

		    #     if _type == "float":
		    #         value = converthex2float(_valueHex)
		    #     elif _type == "signed16":
		    #         value = convertHex2SignedInt16bit(_valueHex)
		    #     elif _type == "unsigned32":
		    #         value = int(_valueHex, 16)
		    #     else:
		    #         print("Something went wrong.")

		    #     print(xy.get('i'), ": ", value/_factor)

		# Just example to navigate through dictionary
		# for _key in dicP:
		#	print(dicP[_key]['desc'])

		print("================= End HTTP object =================")

		#Sende zu Sitelink, wenn nicht gewünscht, nächste Zeile mit "#" auskommentieren
		send2portal('aesitelink.de', 80, rcdvMessageString)
		#Sende zu Refu-log, wenn nicht gewünscht, nächste Zeile mit "#" auskommentieren
		send2portal('refu-log.de', 80, rcdvMessageString)

		# Dem Wechselrichter eine OK Nachricht schicken
		client_serving_socket.send(string2bytes(getokmsg()))
		
		# Close connection
		client_serving_socket.close()
		del client_serving_socket

		f = open('logfile.txt', 'at', encoding='utf-8')
		f.write(r.content)
		f.close()

		"""
		#Werte dekodieren und in csv schreiben
		#Define Pfad für CSV-Files
		datalogfile = "./data/" + time.strftime("%Y_%m_DataSinvert") + '.csv'
		errlogfile = "./error/" + time.strftime("%Y_%m_ErrSinvert") + '.csv'

		#Prüfe ob Störungen oder Daten empfangen wurden
		if rcvdatenstring.find('<rd m="') >= 0:#Wenn Daten empfangen, dann in datalogfile schreiben

			try:#Prüfe ob Datei existiert
				f = open(datalogfile, 'r')
				#lastline = f.readlines()[-1]
				#print(lastline)
				f.close()
			except BaseException as e:#Wenn nicht dann neue Datei erstellen und Spaltenbeschriftung hinzufügen
				print(str(e) + '\r\n')
				initdatalogfile(datalogfile)
			#Daten in File schreiben
			f = open(datalogfile, 'a')
			f.write(decodedata(rcvdatenstring))
			f.close()
			
		elif rcvdatenstring.find('<re m="') >= 0:#Wenn Daten empfangen, dann in errlogfile schreiben

			try:#Prüfe ob Datei existiert
				f = open(errlogfile, 'r')
				#lastline = f.readlines()[-1]
				#print(lastline)
				f.close()
			except BaseException as e:#Wenn nicht dann neue Datei erstellen und Spaltenbeschriftung hinzufügen
				print(str(e) + '\r\n')
				initerrlogfile(errlogfile)
			#Daten in File schreiben
			f = open(errlogfile, 'a')
			f.write(decodeerr(rcvdatenstring))
			f.close()
		else:#Bei falschem Format nur Ausgeben
			print('Falsches Datenformat empfangen!\r\n')
			print(rcvdatenstring)
		"""


# =======================
# Main
# =======================
if __name__ == "__main__":
	try:
		main()
	except BaseException as e:#bei einer Exception Verbindung schließen und neu starten
		print(str(e) + '\r\n')
		server_socket.close()
		del server_socket
