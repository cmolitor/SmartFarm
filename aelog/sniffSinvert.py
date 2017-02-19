import socket
import sys
import struct
import time
"""
Version: RcvSendSinvertDaten_V3.py

Programm zum Empfangen von Daten von Refusol/Sinvert/AdvancedEnergy Wechselrichter
Getestet mit einem Sinvert PVM20 und einem RaspberryPi B

Einstellungen im Wechselrichter:
IP: Freie IP-Adresse im lokalen Netzwerk
Netmask: 255.255.255.0
Gateway: IP-Adresse des Rechners auf dessen dieses Prg läuft(zb. Raspberry),

Einstellungen am Rechner(zb. Raspberry)
routing aktivieren
sudo sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'

Pakete welche an die IP des Logportals gehen and die IP des Raspi umleiten
sudo iptables -t nat -A PREROUTING -d 88.79.234.30 -j DNAT --to-destination ip.des.rasp.berry
sudo iptables -t nat -A PREROUTING -d 195.27.237.106 -j DNAT --to-destination 192.168.0.212

Pakete als absender die IP des Raspi eintragen
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

Damit dies auch nach einem Neustart funktioniert auch in die crontab eintragen:
sudo crontab -e
@reboot sudo iptables -t nat -A PREROUTING -d 88.79.234.30 -j DNAT --to-destination ip.des.rasp.berry;sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

Im Program muss noch die IP des Raspberry geändert werden,
sowie die Pfade datalogfile und errlogfile für den Speicherort der .csv files.
Die Pfade(Ordner) müssen existieren, diese werden nicht automatisch erzeugt!

Start des Programms via Kommandozeile
sudo python3 /home/pi/RcvSendSinvertDaten_V3.py

Benutzung auf eigene Gefahr! Keine Garantie/Gewährleistung.

TODO:
 - Exceptionhandling optimieren
 - Codeoptimierungen...
 - Mailversand wenn Störungen auftreten
 - Störungsnummern wandeln in Störungstext
 - ev. grafische anzeige der Daten...
 - Log Messages ergänzen
"""

#Define Pfad für CSV-Files, sind den eigenen Bedürfnissen anzupassen
#datalogfile = "E:\" + time.strftime("\%Y_%m_DataSinvert") + '.csv' #Beispiel für Windows
#errlogfile = "E:\" + time.strftime("\%Y_%m_ErrSinvert") + '.csv'#Beispiel für Windows
datalogfile = "/home/pi/" + time.strftime("%Y_%m_DataSinvert") + '.csv'
errlogfile = "/home/pi/" + time.strftime("%Y_%m_ErrSinvert") + '.csv'

#Zeichenfolgen für Daten sind bei den verschiedenen Firmwareständen unterschiedlich:
#je nach Firmware mit "#" auskommentieren bzw. einkommentieren

#macaddr,endmacaddr = 'm="','"'#für neuere firmwares
macaddr,endmacaddr = '<m>','</m>'#für ältere firmwares

#firmware,endfirmware = 's="','"'#für neuere firmwares
firmware,endfirmware = '<s>','</s>'#für ältere firmwares

rasp_ip = '192.168.0.212'#IP- des Raspi angeben, wenn keine IP angeben wird ==> Raspi lauscht auf allen zugewiesenen IP Adressen
rasp_port = 80 #Port auf dem das prg am raspi lauscht


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
  return returnval

def send2portal(addr,port,data):
  #Sende zu Sitelink/Refu-Log Portal
  print("Marker 0.1")
  server_addr = (addr, port)
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
    print('Senddata: ' + senddata + ' :EndSenddata\r\n')
    client_socket.send(string2bytes(senddata))#Sende empfangene Daten von WR zu Portal
    daten = client_socket.recv(1024)#Empfange Rückmeldung von Portal
    datenstring = bytes2string(daten)
    print('Reply: ' + datenstring + ' :EndReply\r\n')
  except BaseException as e:
    print(str(e) + '\r\n')

  print("Marker 0.2")
  client_socket.close()
  print("Marker 0.3")
  del client_socket
  print("Marker 0.4")

def getokmsg():
    return ('HTTP/1.1 200 OK'
    +'Cache-Control: private, max-age=0'
    +'Content-Type: text/xml; charset=utf-8\r\n'
    +'Content-Length: 83\r\n'
    +'\r\n'
    +'<?xml version="1.0" encoding="utf-8"?>'
    +'<string xmlns="InverterService">OK</string>\r\n')

#Hole aktuelle Zeit:
def getNTPTime(host = "at.pool.ntp.org"):
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
  try:
    sendcontent = ('<?xml version="1.0" encoding="utf-8"?>'
                   +'<string xmlns="InverterService">&lt;crqr&gt;&lt;c n="SETINVERTERTIME" i="0"&gt;&lt;p n="date" t="3"&gt;'
                   +getNTPTime()
                   +'&lt;/p&gt;&lt;/c&gt;&lt;/crqr&gt;</string>')
    return ('HTTP/1.1 200 OK'
    +'Cache-Control: private, max-age=0'
    +'Content-Type: text/xml; charset=utf-8\r\n'
    +'Content-Length: ' + str(len(sendcontent)) + '\r\n'
    +'\r\n'
    + sendcontent)
  except BaseException as e:
    print(str(e) + '\r\n')
    return getokmsg()#Wenn Zeit holen nicht möglich, nur Ok message schicken

#Hier startet Main prg
def main():
  global server_socket
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
    rcvdatenstring = ''
    block = string2bytes('')
    rcvbytes = string2bytes('')
    server_socket.listen(5)#Socket beobachten
    print('Daten Lesen')
    client_serving_socket, addr = server_socket.accept()
    client_serving_socket.settimeout(5)
  
    print("================= Begin new message =================")
    while True:
      try:
        rcvbytes = client_serving_socket.recv(1024)#Daten empfangen
        # print(bytes2string(rcvbytes))
        rcvdatenstring = rcvdatenstring + bytes2string(rcvbytes)
        rcvok = rcvdatenstring.find('xmlData')
        print(rcvok)
      except BaseException as e:
        print(str(e) + '\r\n')
        print(rcvbytes)
      if (rcvok >= 0) or (not rcvbytes):#Solange Daten lesen, bis xmlData empfangen wurden
        block = block+rcvbytes
        break
      else:
        block = block+rcvbytes
        rcvbytes = string2bytes('')

    print("================= End new message =================")

    f = open('logfile_sniffer.txt', 'at', encoding='utf-8')
    f.write(rcvdatenstring)
    f.close()

    #Sende zu Sitelink, wenn nicht gewünscht, nächste Zeile mit "#" auskommentieren
    #send2portal('aesitelink.de', 80, rcvdatenstring)
    #Sende zu Refu-log, wenn nicht gewünscht, nächste Zeile mit "#" auskommentieren
    send2portal('refu-log.de', 80, rcvdatenstring)    

    print("Marker 1")
    #Werte dekodieren und in csv schreiben

    #Prüfe ob Störungen oder Daten empfangen wurden
    if rcvdatenstring.find('<rd') >= 0:#Wenn Daten empfangen, dann in datalogfile schreiben
      print("Marker 2")
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
      #Dem WR eine OK Nachricht schicken
      client_serving_socket.send(string2bytes(getokmsg()))
      print("Marker 3")
    elif rcvdatenstring.find('<re') >= 0:#Wenn Errordaten empfangen, dann in errlogfile schreiben
      print("Marker 4")
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
      #Dem WR eine OK Nachricht schicken
      client_serving_socket.send(string2bytes(getokmsg()))
      print("Marker 5")
    elif rcvdatenstring.find('<crq>') >= 0:#Wenn Steuerdaten empfangen, dann in Uhrzeit setzen
      #Dem WR aktuelle Uhrzeit schicken schicken
      client_serving_socket.send(string2bytes(gettimemsg()))
      print("Marker 6")
    else:#Bei falschem Format nur Ausgeben
      print("Marker 7")
      print('Falsches Datenformat empfangen!\r\n')
      print(rcvdatenstring)
      print(' :End Falsches Datenformat empfangen!\r\n')
      #Dem WR eine OK Nachricht schicken
      client_serving_socket.send(string2bytes(getokmsg()))
      print("Marker 8")

    #Verbindung schließen
    client_serving_socket.close()
    del client_serving_socket
    print("Marker 9")


while True:
  try:
    main()
  except BaseException as e:#bei einer Exception Verbindung schließen und neu starten
    print(str(e) + '\r\n')
    server_socket.close()
    del server_socket
  time.sleep(10)#10s warten
#ServerEnde
