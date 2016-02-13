# Hardware description

- Socomec Diris A40
- ETHERNET MODULE WITH MODBUS RTU GATEWAY – Ref. 48250204:
   - MODBUS master gateway with RS485 3-point link with TCP.
   - MODBUS TCP and MODBUS RTU protocols.
   - WEB-server for product configuration, displaying the values and the diagnostics.

- Serial number 1: 1548231
- Serial number 2: 0009

# Boot script for starting metec_core properly

## General on boot scripts

Create script in this folder with your commands. Here: `boot.sh`.

Make script executbale:
```
sudo chmod 755 boot.sh 
```

Add to the file:

```
sudo nano /etc/rc.local
```

the following line (example):

```
sudo /home/pi/pySocoLogger/boot.sh
```

