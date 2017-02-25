#!/usr/bin/python3
# -*- coding: utf-8 -*-
import socket
import sys
import struct
import time
import pickle
import json


minpythonversion = 0x3020000
if sys.hexversion < minpythonversion:
  print('Python version ' + str(sys.version) + ' is too old, please use Python version 3.2 or newer!')
  sys.exit()
"""
Version 4:
-- Anbindung zu Volkszähler ergänzt
-- Logging ergänzt
-- # -*- coding: utf-8 -*- und überprüfung der Python version ergänzt
-- Standardmäßig wird jetzt Port 8080 für dieses prg verwendent, da auf port 80 der Dateizugriff auf den raspi manchmal nicht funktioniert(iptables müssen auch angepasst werden)
-- Weiterleitung der Rohdaten vom WR jetzt über Schleife realisiert, 
Programm zum Empfangen von Daten von Refusol/Sinvert/AdvancedEnergy Wechselrichter
Getestet mit einem Sinvert PVM20 und einem RaspberryPi B

Einstellungen im Wechselrichter:
IP: Freie IP-Adresse im lokalen Netzwerk
Netmask: 255.255.255.0
Gateway: IP-Adresse des Rechners auf dessen dieses Prg läuft(zb. Raspberry),

Einstellungen am Rechner(zb. Raspberry)
routing aktivieren
sudo sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'

Pakete welche an die IP des Logportals gehen and die IP des Raspi umleiten und auf port 8080
sudo iptables -t nat -A PREROUTING -d 88.79.234.30 -j DNAT --to-destination ip.des.rasp.berry --dport 8080

Pakete als absender die IP des Raspi eintragen
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

Damit dies auch nach einem Neustart funktioniert auch in die crontab eintragen:
sudo crontab -e
@reboot sudo iptables -t nat -A PREROUTING -d 88.79.234.30 -j DNAT --to-destination ip.des.rasp.berry;sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

Im Program muss noch die IP des Raspberry geändert werden,
sowie die Pfade datalogpath, errlogpath, und loggingpath für den Speicherort der .csv files. Standard: "/home/pi/"
Die Pfade(Ordner) müssen existieren, diese werden nicht automatisch erzeugt!

Start des Programms via Kommandozeile
sudo python3 /home/pi/RcvSendSinvertDaten_V4.py

Damit nach Neustart automatisch gestartet wird in crontab eintragen:
sudo crontab -e
@reboot sudo python3 /home/pi/RcvSendSinvertDaten_V4.py

Benutzung auf eigene Gefahr! Keine Garantie/Gewährleistung/Schadenersatzansprüche.

TODO:
 - Exceptionhandling optimieren
 - Codeoptimierungen...
 - Mailversand wenn Störungen auftreten
 - Störungsnummern wandeln in Störungstext
"""

#Define Pfad für CSV-Files, sind den eigenen Bedürfnissen anzupassen 
#datalogfile = "E:\" + time.strftime("\%Y_%m_DataSinvert") + '.csv' #Beispiel für Windows
#errlogfile = "E:\" + time.strftime("\%Y_%m_ErrSinvert") + '.csv'#Beispiel für Windows
datalogpath = "/home/pi/"
errlogpath = "/home/pi/"
loggingpath = "/home/pi/"
datalogfilename = 'DataSinvert.csv'
errlogfilename = 'ErrSinvert.csv'
loggingfilename = 'LoggingSinvert.txt'

#Logfilepfad initialisieren
datalogfile = datalogpath + time.strftime("%Y_%m_") + datalogfilename
errlogfile = errlogpath + time.strftime("%Y_%m_") + errlogfilename
loggingfile = loggingpath + time.strftime("%Y_%m_") + loggingfilename

#Zeichenfolgen für Daten sind bei den verschiedenen Firmwareständen unterschiedlich:
#je nach Firmware mit "#" auskommentieren bzw. einkommentieren

#macaddr,endmacaddr = 'm="','"'#für neuere firmwares
macaddr,endmacaddr = '<m>','</m>'#für ältere firmwares

#firmware,endfirmware = 's="','"'#für neuere firmwares
firmware,endfirmware = '<s>','</s>'#für ältere firmwares

rasp_ip = '192.168.0.212' #IP- des Raspi angeben, wenn keine IP angeben wird ==> Raspi lauscht auf allen zugewiesenen IP Adressen
rasp_port = 8080 #Port auf dem das prg am raspi lauscht

#Server, an dessen die Daten 1:1 durchgereicht werden, Format: [('ipserver1',portserver1),('ipserver2',portserver2),usw...]
#Es können beliebig viele Server angegeben werden, diese werden in einer Schleife abgearbeitet
#Wenn an keine Server weitergereicht werden soll, dann: rawdataserver = []
rawdataserver = [('refu-log.de', 80)]


#Konfiguration Volkszählerserver:
#Sende Daten an Volkszählerserver: vz = 1, nicht an volkszähler senden: vz = 0
vz = 0
#IP-Adresse und Port des Volkszählerservers, wenn Volkszähler auf dem selben rechner läuft wie dieses Programm, dann localhost angeben: vz_ip = ('127.0.0.1',80)
vz_adress = ('10.0.0.13',80)

#init logstring
logstring = ''

if vz:
  try:
    import volkszählertestV2 as vzlogger
    vzlogger.vzinit(vz_adress)
  except BaseException as e:
    vz = 0
    print('Fehler beim import der Volkszähleranbindung, Volkszähler wird deaktiviert')
    print(str(e) + '\r\n')
    logstring += str(e) + '\r\n' + 'Fehler beim import der Volkszähleranbindung, Volkszähler wird deaktiviert\r\n'

def byteorder():
  global logstring
  return sys.byteorder

def standard_encoding():
  return sys.getdefaultencoding()

def standardausgabe_encoding():
  global logstring
  return sys.stdout.encoding

def string2bytes(text):
  global logstring
  return bytes(text, "cp1252")

def bytes2string(bytes):
  global logstring
  return str(bytes, "cp1252")

def converthex2float(hexval):
  global logstring
  #print(hexval)
  try:
    return round(struct.unpack('>f', struct.pack('>I', int(float.fromhex(hexval))))[0],2)
  except BaseException as e:
    print(str(e) + '\r\n')
    logstring += str(e) + '\r\n' + 'Error while convert hex to float failed! hexvalue = ' + str(hexval) + '\r\n'
    return 0

def converthex2int(hexval):
  global logstring
  #print(hexval)
  try:
    return struct.unpack('>i', struct.pack('>I', int(float.fromhex(hexval))))[0]
  except BaseException as e:
    print(str(e) + '\r\n')
    logstring += str(e) + '\r\n' + 'Error while convert hex to int failed! hexvalue = ' + str(hexval) + '\r\n'
    return 0

def initdatalogfile(datalogfile):
  global logstring
  string = []

  string.append('MAC-Adresse')
  string.append('Seriennummer')
  string.append('Zeitstempel')
  string.append('Loggerinterval')
  string.append('AC Momentanleistung [W]')
  string.append('AC Netzspannung [V]')
  string.append('AC Strom [A]')
  string.append('AC Frequenz [Hz]')
  string.append('DC Momentanleistung [W]')
  string.append('DC-Spannung [V]')
  string.append('DC-Strom [A]')
  string.append('Temperatur 1 Kühlkörper rechts [°C]')
  string.append('Temperatur 2 innen oben links [°C]')
  string.append('Sensor 1 Messwert, Einstrahlung [W/m²]')
  string.append('Sensor 2 Messwert, Modultemperatur [°C]')
  string.append('Tagesertrag [kwh]')
  string.append('Status')
  string.append('Gesamtertrag [kwh]')
  string.append('Betriebsstunden [h]')
  string.append('scheinbar nur ältere FW?')
  string.append('"neuere" FW: 100.0% Leistungsbeschränkung [%]')
  string.append('"neuere" FW, vielleicht: 0.0 kWh Tagessonnenenergie')
  returnval = (str(string).replace("', '",';').replace("['",'').replace("']",'\r\n'))
  f = open(datalogfile, 'a')
  f.write(returnval)
  f.close()

def initerrlogfile(errlogfile):
  global logstring
  string = []

  string.append('MAC-Adresse')
  string.append('Seriennummer')
  string.append('Zeitstempel')
  string.append('Errorcode')
  string.append('State')
  string.append('Short')
  string.append('Long')
  string.append('Type')
  string.append('Actstate')
  returnval = (str(string).replace("', '",';').replace("['",'').replace("']",'\r\n'))
  f = open(errlogfile, 'a')
  f.write(returnval)
  f.close()

def decodedata(rcv):#Daten decodieren
  global logstring
  string = []

  index = macaddr
  endindex = endmacaddr
  if rcv.find(index) >= 0:
    string.append(str(rcv[rcv.find(index)+3:rcv.find(endindex,rcv.find(index)+3)]))
  else:
    string.append('0')
  index = firmware
  endindex = endfirmware
  if rcv.find(index) >= 0:
    string.append(str(rcv[rcv.find(index)+3:rcv.find(endindex,rcv.find(index)+3)]))
  else:
    string.append('0')
  index = 't="'
  if rcv.find(index) >= 0:
    timestamp = int((rcv[rcv.find(index)+3:rcv.find('"',rcv.find(index)+3)]))
    string.append(time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp)))
  else:
    string.append('0')
  index = '" l="'
  if rcv.find(index) >= 0:
    string.append(str((rcv[rcv.find(index)+5:rcv.find('"',rcv.find(index)+5)])))
  else:
    string.append('0')
  index = 'i="1"'
  if rcv.find(index) >= 0:
    acleistung = str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))]))
    string.append(acleistung)
  else:
    string.append('0')
  index = 'i="2"'
  if rcv.find(index) >= 0:
    acspannung = str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))]))
    string.append(acspannung)
  else:
    string.append('0')
  index = 'i="3"'
  if rcv.find(index) >= 0:
    acstrom = str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))]))
    string.append(acstrom)
  else:
    string.append('0')
  index = 'i="4"'
  if rcv.find(index) >= 0:
    acfrequenz = str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))]))
    string.append(acfrequenz)
  else:
    string.append('0')
  index = 'i="5"'
  if rcv.find(index) >= 0:
    dcleistung = str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))]))
    string.append(dcleistung)
  else:
    string.append('0')
  index = 'i="6"'
  if rcv.find(index) >= 0:
    dcspannung = str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))]))
    string.append(dcspannung)
  else:
    string.append('0')
  index = 'i="7"'
  if rcv.find(index) >= 0:
    dcstrom = str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))]))
    string.append(dcstrom)
  else:
    string.append('0')
  index = 'i="8"'
  if rcv.find(index) >= 0:
    temp1 = str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10)
    string.append(temp1)
  else:
    string.append('0')
  index = 'i="9"'
  if rcv.find(index) >= 0:
    temp2 = str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10)
    string.append(temp2)
  else:
    string.append('0')
  index = 'i="A"'
  if rcv.find(index) >= 0:
    einstrahlung = str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])) + ''
    string.append(einstrahlung)
  else:
    string.append('0')
  index = 'i="B"'
  if rcv.find(index) >= 0:
    modultemp = str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])) + ''
    string.append(modultemp)
  else:
    string.append('0')
  index = 'i="C"'
  if rcv.find(index) >= 0:
    tagesertrag = str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10)
    string.append(tagesertrag)
  else:
    string.append('0')
  index = 'i="D"'
  if rcv.find(index) >= 0:
    status = str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))]))
    string.append(status)
  else:
    string.append('0')
  index = 'i="E"'
  if rcv.find(index) >= 0:
    gesamtertrag = str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10)
    string.append(gesamtertrag)
  else:
    string.append('0')
  index = 'i="F"'
  if rcv.find(index) >= 0:
    betriebsstunden = str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10)
    string.append(betriebsstunden)
  else:
    string.append('0')
  index = 'i="10"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+7:rcv.find('<',rcv.find(index))])/10))
  else:
    string.append('0')
  index = 'i="12"'
  if rcv.find(index) >= 0:
    leistungsbesch = str(converthex2int(rcv[rcv.find(index)+7:rcv.find('<',rcv.find(index))])/10)
    string.append(leistungsbesch)
  else:
    string.append('0')
  index = 'i="11"'
  if rcv.find(index) >= 0:
    tagessonnenenergie = str(converthex2int(rcv[rcv.find(index)+7:rcv.find('<',rcv.find(index))])/10)
    string.append(tagessonnenenergie)
  else:
    string.append('0')
  returnval = (str(string).replace("', '",';').replace("['",'').replace("']",'\r\n').replace(".",','))
  logstring += 'Decoded data:' + '\r\n' + returnval + '\r\n'
  print(returnval)
  return returnval

def decodeerr(rcv):#Störungen decodieren
  global logstring
  string = []

  index = macaddr
  if rcv.find(index) >= 0:
    string.append(str(rcv[rcv.find(index)+3:rcv.find('"',rcv.find(index)+3)]))
  else:
    string.append('0')
  index = firmware
  if rcv.find(index) >= 0:
    string.append(str(rcv[rcv.find(index)+3:rcv.find('"',rcv.find(index)+3)]))
  else:
    string.append('0')
  index = 't="'
  if rcv.find(index) >= 0:
    string.append(time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int((rcv[rcv.find(index)+3:rcv.find('"',rcv.find(index)+3)])))))
  else:
    string.append('0')
  index = '<code>'
  if rcv.find(index) >= 0:
    string.append(str((rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index)+6)])))
  else:
    string.append('0')
  index = '<state>'
  if rcv.find(index) >= 0:
    string.append(str((rcv[rcv.find(index)+7:rcv.find('<',rcv.find(index)+7)])))
  else:
    string.append('0')
  index = '<short>'
  if rcv.find(index) >= 0:
    string.append(str((rcv[rcv.find(index)+7:rcv.find('<',rcv.find(index)+7)])))
  else:
    string.append('0')
  index = '<long>'
  if rcv.find(index) >= 0:
    string.append(str((rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index)+6)])))
  else:
    string.append('0')
  index = '<type>'
  if rcv.find(index) >= 0:
    string.append(str((rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index)+6)])))
  else:
    string.append('0')
  index = '<actstate>'
  if rcv.find(index) >= 0:
    string.append(str((rcv[rcv.find(index)+10:rcv.find('<',rcv.find(index)+10)])))
  else:
    string.append('0')
  returnval = (str(string).replace("', '",';').replace("['",'').replace("']",'\r\n').replace(".",','))
  print(returnval)
  logstring += 'Decoded errors:' + '\r\n' + returnval + '\r\n'
  return returnval

def send2portal(server_addr,data):
    global logstring
    #Sende zu Sitelink/Refu-Log Portal
    print(server_addr)
    try:
      client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      client_socket.settimeout(5)
      client_socket.connect(server_addr)
      sendcontent = data[data.find('xmlData'):]
      senddata = ('POST /InverterService/InverterService.asmx/CollectInverterData HTTP/1.1\r\n'
                  +'Host: refu-log.de\r\n'
                  +'Content-Type: application/x-www-form-urlencoded\r\n'
                  +'Content-Length: ' + str(len(sendcontent)) + '\r\n'
                  +'\r\n'
                  + sendcontent)
      #print('Senddata: ' + senddata)
      client_socket.send(string2bytes(senddata))#Sende empfangene Daten von WR zu Portal
      logstring += 'Sende Daten zu ' + str(server_addr) + ':\r\n' + str(sendcontent) + '\r\n'
      daten = client_socket.recv(1024)#Empfange Rückmeldung von Portal
      datenstring = bytes2string(daten)
      #print(datenstring)
      logstring += 'Empfange Daten von ' + str(server_addr) + ':\r\n' + str(datenstring) + '\r\n'
    except BaseException as e:
      print(str(e) + '\r\n')
      logstring += str(e) + '\r\n' + 'Sending data to ' + str(server_addr) + ' failed!' + '\r\n'
    client_socket.close()
    del client_socket

def send2vz(server_addr,csvdata):
    global logstring
    #Sende zu Volkszählerserver
    print(server_addr)
    try:
      #print(csvdata)
      data = csvdata.replace(',','.').split(';')
      #print(data)
      timestamp = str(int(time.mktime(time.strptime(data[2],'%Y-%m-%d %H:%M:%S')) * 1000))#Format in millisekunden und UTC für volkszähler
      print(timestamp)
      #print(vzlogger.storedata(server_addr,vzlogger.parameter['mac']['uuid'],timestamp,data[0]))
      #print(vzlogger.storedata(server_addr,vzlogger.parameter['serial']['uuid'],timestamp,data[1]))
  string.append('MAC-Adresse')
  string.append('Seriennummer')
  string.append('Zeitstempel')
  string.append('Loggerinterval')
  string.append('AC Momentanleistung [W]')
  string.append('AC Netzspannung [V]')
  string.append('AC Strom [A]')
  string.append('AC Frequenz [Hz]')
  string.append('DC Momentanleistung [W]')
  string.append('DC-Spannung [V]')
  string.append('DC-Strom [A]')
  string.append('Temperatur 1 Kühlkörper rechts [°C]')
  string.append('Temperatur 2 innen oben links [°C]')
  string.append('Sensor 1 Messwert, Einstrahlung [W/m²]')
  string.append('Sensor 2 Messwert, Modultemperatur [°C]')
  string.append('Tagesertrag [kwh]')
  string.append('Status')
  string.append('Gesamtertrag [kwh]')
  string.append('Betriebsstunden [h]')
  string.append('scheinbar nur ältere FW?')
  string.append('"neuere" FW: 100.0% Leistungsbeschränkung [%]')
  string.append('"neuere" FW, vielleicht: 0.0 kWh Tagessonnenenergie')
      print(vzlogger.storedata(server_addr,vzlogger.parameter['timestamp']['uuid'],timestamp,timestamp))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['interval']['uuid'],timestamp,data[3]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['acleistung']['uuid'],timestamp,data[4]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['acspannung']['uuid'],timestamp,data[5]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['acstrom']['uuid'],timestamp,data[6]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['acfrequenz']['uuid'],timestamp,data[7]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['dcleistung']['uuid'],timestamp,data[8]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['dcspannung']['uuid'],timestamp,data[9]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['dcstrom']['uuid'],timestamp,data[10]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['temp1']['uuid'],timestamp,data[11]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['temp2']['uuid'],timestamp,data[12]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['einstrahlung']['uuid'],timestamp,data[13]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['modultemp']['uuid'],timestamp,data[14]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['tagesertrag']['uuid'],timestamp,data[15]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['status']['uuid'],timestamp,data[16]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['gesamtertrag']['uuid'],timestamp,data[17]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['betriebsstunden']['uuid'],timestamp,data[18]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['index10']['uuid'],timestamp,data[19]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['leistungsbesch']['uuid'],timestamp,data[20]))
      print(vzlogger.storedata(server_addr,vzlogger.parameter['sonnenenergie']['uuid'],timestamp,data[21]))

    except BaseException as e:
      print(str(e) + '\r\n')
      logstring += str(e) + '\r\n' + 'Sending data to ' + str(server_addr) + ' failed!' + '\r\n'

def getokmsg():
    global logstring
    sendcontent = ('HTTP/1.1 200 OK'
    +'Cache-Control: private, max-age=0'
    +'Content-Type: text/xml; charset=utf-8\r\n'
    +'Content-Length: 83\r\n'
    +'\r\n'
    +'<?xml version="1.0" encoding="utf-8"?>'
    +'<string xmlns="InverterService">OK</string>\r\n')
    logstring += 'Sende Daten zu WR:' + '\r\n' + sendcontent + '\r\n'
    return sendcontent

#Hole aktuelle Zeit:
def getNTPTime(host = "at.pool.ntp.org"):
  global logstring
  port = 123
  buf = 1024
  address = (host,port)
  msg = '\x1b' + 47 * '\0'

  # reference time (in seconds since 1900-01-01 00:00:00)
  TIME1970 = 2208988800 # 1970-01-01 00:00:00

  # connect to server
  client_socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM)
  client_socket.sendto(string2bytes(msg), address)
  msg, address = client_socket.recvfrom( buf )
  t = struct.unpack( "!12I", msg )[10]
  t -= TIME1970
  client_socket.close()
  del client_socket
  return time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(t))

def gettimemsg():
  global logstring
  try:
    sendcontent = ('<?xml version="1.0" encoding="utf-8"?>'
                   +'<string xmlns="InverterService">&lt;crqr&gt;&lt;c n="SETINVERTERTIME" i="0"&gt;&lt;p n="date" t="3"&gt;'
                   +getNTPTime()
                   +'&lt;/p&gt;&lt;/c&gt;&lt;/crqr&gt;</string>')
    logstring += 'Sende Daten zu WR:' + '\r\n' + sendcontent + '\r\n'
    return ('HTTP/1.1 200 OK'
    +'Cache-Control: private, max-age=0'
    +'Content-Type: text/xml; charset=utf-8\r\n'
    +'Content-Length: ' + str(len(sendcontent)) + '\r\n'
    +'\r\n'
    + sendcontent)
  except BaseException as e:
    print('Can`t get NTP-Time' + str(e) + '\r\n')
    logstring += str(e) + '\r\n' + 'Can`t get NTP-Time!' + '\r\n'
    return getokmsg()#Wenn Zeit holen nicht möglich, nur Ok message schicken

#Hier startet Main prg
def main():
  global logstring
  global vz_adress
  global vz
  global rawdataserver
  #Init TCP-Server
  server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)#Bei Neustart wiederverwenden des Sockets ermöglichen
  #Server binden mit der IP des Raspi
  #server_socket.bind((socket.gethostbyname(socket.gethostname()), 80))
  #Raspi muss eine fixe IP haben!
  #server_socket.bind(('10.0.0.25', 80))
  server_socket.bind((rasp_ip, rasp_port))#Keine IP angeben ==> Raspi lauscht auf allen zugewiesenen IP Adressen

  #print(socket.gethostbyname(socket.gethostname()))
  while True:
    print('Listen for Data')
    logstring += 'Listen for Data...' + '\r\n'
    rcvdatenstring = ''
    block = string2bytes('')
    rcvbytes = string2bytes('')
    server_socket.listen(5)#Socket beobachten
    client_serving_socket, addr = server_socket.accept()
    client_serving_socket.settimeout(5)
  
    while True:
      try:
        rcvbytes = client_serving_socket.recv(1024)#Daten empfangen
        #print(bytes2string(rcvbytes))
        rcvdatenstring = rcvdatenstring + bytes2string(rcvbytes)
        rcvok = rcvdatenstring.find('xmlData')
        logstring += 'Daten von WR empfangen!' + '\r\n' + str(rcvbytes) + '\r\n'
        #print(rcvok)
      except BaseException as e:
        print(str(e) + '\r\n')
        print(rcvbytes)
        logstring += str(e) + '\r\n' + 'Error während lesen von WR!' + '\r\n' + str(rcvbytes) + '\r\n'
      if (rcvok >= 0) or (not rcvbytes):#Solange Daten lesen, bis xmlData empfangen wurden
        block = block+rcvbytes
        break
      else:
        block = block+rcvbytes
        rcvbytes = string2bytes('')
    

    #Werte dekodieren und in csv schreiben
    #Logfilepfad initialisieren
    datalogfile = datalogpath + time.strftime("%Y_%m_") + datalogfilename
    errlogfile = errlogpath + time.strftime("%Y_%m_") + errlogfilename
    loggingfile = loggingpath + time.strftime("%Y_%m_") + loggingfilename
    #Prüfe ob Störungen oder Daten empfangen wurden
    if rcvdatenstring.find('<rd') >= 0:#Wenn Daten empfangen, dann in datalogfile schreiben

      try:#Prüfe ob Datei existiert
        f = open(datalogfile, 'r')
        #lastline = f.readlines()[-1]
        #print(lastline)
        f.close()
      except BaseException as e:#Wenn nicht dann neue Datei erstellen und Spaltenbeschriftung hinzufügen
        print(str(e) + '\r\n')
        logstring += str(e) + '\r\n' + 'Datalogfile existiert nicht ==> neues erstellen!' + '\r\n'
        initdatalogfile(datalogfile)
      csvdata = decodedata(rcvdatenstring)
      #Daten in File schreiben
      f = open(datalogfile, 'a')
      f.write(csvdata)
      f.close()
      #Dem WR eine OK Nachricht schicken
      client_serving_socket.send(string2bytes(getokmsg()))
      
    elif rcvdatenstring.find('<re') >= 0:#Wenn Errordaten empfangen, dann in errlogfile schreiben

      try:#Prüfe ob Datei existiert
        f = open(errlogfile, 'r')
        #lastline = f.readlines()[-1]
        #print(lastline)
        f.close()
      except BaseException as e:#Wenn nicht dann neue Datei erstellen und Spaltenbeschriftung hinzufügen
        print(str(e) + '\r\n')
        logstring += str(e) + '\r\n' + 'Errorlogfile existiert nicht ==> neues erstellen!' + '\r\n'
        initerrlogfile(errlogfile)
      #Daten in File schreiben
      f = open(errlogfile, 'a')
      f.write(decodeerr(rcvdatenstring))
      f.close()
      #Dem WR eine OK Nachricht schicken
      client_serving_socket.send(string2bytes(getokmsg()))
      
    elif rcvdatenstring.find('<crq>') >= 0:#Wenn Steuerdaten empfangen, dann in Uhrzeit setzen
      #Dem WR aktuelle Uhrzeit schicken schicken
      client_serving_socket.send(string2bytes(gettimemsg()))


    else:#Bei falschem Format nur Ausgeben
      print('Falsches Datenformat empfangen!\r\n')
      print(rcvdatenstring)
      logstring += 'Falsches Datenformat empfangen!\r\n' + rcvdatenstring[rcvdatenstring.find('xmlData'):] + '\r\n'
      #Dem WR eine OK Nachricht schicken
      client_serving_socket.send(string2bytes(getokmsg()))

    #Verbindung schließen
    client_serving_socket.close()
    del client_serving_socket
    #Daten in Loggingfile schreiben
    f = open(loggingfile, 'a')
    f.write(logstring)
    f.close()
    logstring = ''

    #Sende zu Datenbankserver, wenn nicht gewünscht, nächste Zeile mit "#" auskommentieren
    for adress in rawdataserver:
      send2portal(adress, rcvdatenstring)
    #Sende zu Volkszählerserver
    if vz:
      send2vz(vz_adress, csvdata)

#Hauptschleife
while True:
  try:
    main()
  except BaseException as e:#bei einer Exception Verbindung schließen und neu starten
    print(str(e) + '\r\n')
    f = open(loggingfile, 'a')
    f.write(logstring)
    f.close()
    logstring = ''
    server_socket.close()
    del server_socket
  time.sleep(10)#10s warten
#ServerEnde
