import socket
import sys
import struct
import time
from http.client import HTTPResponse
from io import StringIO

"""
Programm zum Empfangen von Daten von Refusol/Sinvert/AdvancedEnergy Wechselrichter
Getestet mit einem Sinvert PVM20 und einem RaspberryPi B

Einstellungen im Wechselrichter:
IP: Freie IP-Adresse im lokalen Netzwer
Netmask: 255.255.255.0
Gateway: IP-Adresse des Rechners auf dessen dieses Prg läuft(zb. Raspberry),

Einstellungen am Rechner(zb. Raspberry)
routing aktivieren
sudo sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'

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

Im Program muss in der main schleife noch die IP des Raspberry geändert werden,
sowie die Pfade datalogfile und errlogfile für den Speicherort der .csv files.
Die Pfade müssen existieren, diese werden nicht automatisch erzeugt!

Start des Programms via Kommandozeile
sudo python3 /home/pi/Progs/RcvSendSinvertDaten_V2.py

Benutzung auf eigene Gefahr! Keine Garantie/Gewährleistung

TODO:
 - Exceptionhandling optimieren
 - Mailversand wenn Störungen auftreten
 - ev. grafische anzeige der Daten...
"""

class FakeSocket():
  def __init__(self, response_str):
    self._file = StringIO(response_str)
  def makefile(self, *args, **kwargs):
    return self._file

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

def initdatalogfile(datalogfile):
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
  string.append('optional, vielleicht: Einstrahlung')
  string.append('optional, vielleicht: Modultemperatur')
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
  string = []

  index = 'm="'
  if rcv.find(index) >= 0:
    string.append(str(rcv[rcv.find(index)+3:rcv.find('"',rcv.find(index)+3)]))
  else:
    string.append('0')
  index = 's="'
  if rcv.find(index) >= 0:
    string.append(str(rcv[rcv.find(index)+3:rcv.find('"',rcv.find(index)+3)]))
  else:
    string.append('0')
  index = 't="'
  if rcv.find(index) >= 0:
    string.append(time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int((rcv[rcv.find(index)+3:rcv.find('"',rcv.find(index)+3)])))))
  else:
    string.append('0')
  index = '" l="'
  if rcv.find(index) >= 0:
    string.append(str((rcv[rcv.find(index)+5:rcv.find('"',rcv.find(index)+5)])))
  else:
    string.append('0')
  index = 'i="1"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])))
  else:
    string.append('0')
  index = 'i="2"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])))
  else:
    string.append('0')
  index = 'i="3"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])))
  else:
    string.append('0')
  index = 'i="4"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])))
  else:
    string.append('0')
  index = 'i="5"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])))
  else:
    string.append('0')
  index = 'i="6"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])))
  else:
    string.append('0')
  index = 'i="7"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])))
  else:
    string.append('0')
  index = 'i="8"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10))
  else:
    string.append('0')
  index = 'i="9"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10))
  else:
    string.append('0')
  index = 'i="A"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])) + '')
  else:
    string.append('0')
  index = 'i="B"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2float(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])) + '')
  else:
    string.append('0')
  index = 'i="C"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10))
  else:
    string.append('0')
  index = 'i="D"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])))
  else:
    string.append('0')
  index = 'i="E"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10))
  else:
    string.append('0')
  index = 'i="F"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+6:rcv.find('<',rcv.find(index))])/10))
  else:
    string.append('0')
  index = 'i="10"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+7:rcv.find('<',rcv.find(index))])/10))
  else:
    string.append('0')
  index = 'i="12"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+7:rcv.find('<',rcv.find(index))])/10))
  else:
    string.append('0')
  index = 'i="11"'
  if rcv.find(index) >= 0:
    string.append(str(converthex2int(rcv[rcv.find(index)+7:rcv.find('<',rcv.find(index))])/10))
  else:
    string.append('0')
  returnval = (str(string).replace("', '",';').replace("['",'').replace("']",'\r\n').replace(".",','))
  print(returnval)
  return returnval

def decodeerr(rcv):#Störungen decodieren
  string = []

  index = 'm="'
  if rcv.find(index) >= 0:
    string.append(str(rcv[rcv.find(index)+3:rcv.find('"',rcv.find(index)+3)]))
  else:
    string.append('0')
  index = 's="'
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
  return returnval

#Hier startet Main prg
def main():
  global server_socket
  #Init TCP-Server
  server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  #Server binden mit der IP des Raspi
  #server_socket.bind((socket.gethostbyname(socket.gethostname()), 80))
  #Raspi muss eine fixe IP haben!
  server_socket.bind(('192.168.0.212', 80))

  while True:
    print('Listen for Data')
    rcvdatenstring = ''
    block = string2bytes('')
    server_socket.listen(5)#Socket beobachten
    print('Daten Lesen')
    client_serving_socket, addr = server_socket.accept()
    i = 0

    while True:
      i = i + 1
      rcvbytes = client_serving_socket.recv(1024) # Daten empfangen
      print("----------- Beginn Datenpaket: ", i, " -----------------------------")
      print(bytes2string(rcvbytes))
      print("----------- Ende Datenpaket -----------------------------")

      rcvdatenstring = rcvdatenstring + bytes2string(rcvbytes)
      rcvok = rcvdatenstring.find('xmlData')
      print(rcvok)
      if rcvok >= 0:#Solange Daten lesen, bis xmlData empfangen wurden
        block = block+rcvbytes
        break
      else:
        block = block+rcvbytes

    print("================= Beginn Daten =================")
    print(bytes2string(block))
    print("================= Ende Daten =================")

    source = FakeSocket(bytes2string(block))
    print("ok 1")
    response = HTTPResponse(source)
    print("ok 2")
    response.begin()
    print("ok 3")

    print("single header:", response.getheader('Content-Type'))

    """
    #Sende zu Sitelink
    server_addr = ('aesitelink.de', 80)
    print(server_addr)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_addr)
    client_socket.send(block)
    print(bytes2string(block))
    
    daten = client_socket.recv(1024)
    datenstring = bytes2string(daten)
    print(datenstring)
    """
    
    """
    #Sende zu Refulog
    server_addr = ('refu-log.de', 80)
    print(server_addr)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_addr)
    client_socket.send(block)#Sende empfangene Daten von WR zu Portal
    daten = client_socket.recv(1024)#Empfange Rückmeldung von Portal
    datenstring = bytes2string(daten)
    print("Begin Datenstring refu-log.de-----------------------------")
    print(datenstring)
    print("Ende  Datenstring refu-log.de-----------------------------")
    

    client_socket.close()
    del client_socket

    """
    

    #Dem WR eine OK Nachricht schicken
    client_serving_socket.send(string2bytes('HTTP/1.1 200 OK'
    +'Cache-Control: private, max-age=0'
    +'Content-Type: text/xml; charset=utf-8\r\n'
    +'Content-Length: 83\r\n'
    +'\r\n'
    +'<?xml version="1.0" encoding="utf-8"?>'
    +'<string xmlns="InverterService">OK</string>\r\n'))

    client_serving_socket.close()
    del client_serving_socket


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

#while True:
try:
  main()
except BaseException as e:#bei einer Exception Verbindung schließen und neu starten
  print(str(e) + '\r\n')
  server_socket.close()
  del server_socket
#ServerEnde
