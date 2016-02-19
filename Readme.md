# General

Project to read data from Socomec Diris A40 via ModbusTCP and storing data in volkszaehler (VZ) middleware and database.
Furthermore, the idea is to send control signals to a Siemens Logo.
In the very future, some optimization could play a role which will make use of the solver `glpk` and it's python interface pyomo.

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
/home/pi/pySocoLogger/boot.sh
```

# Install Snap7 for communication with Siemens SPS

Manual according to: http://simplyautomationized.blogspot.de/2014/12/raspberry-pi-getting-data-from-s7-1200.html

## General steps

- Download and compile snap7 from http://sourceforge.net/projects/snap7
- Download and install python library to use snap7

## Download and compile snap7 for RPi

Use the following commands but maybe newer paths:
```
wget http://sourceforge.net/projects/snap7/files/1.2.1/snap7-full-1.2.1.tar.gz/download 
tar -zxvf snap7-full-1.2.1.tar.gz
cd snap7-full-1.2.1/build/unix
```

If RPi B, B+:
```
sudo make –f arm_v6_linux.mk all
```

If RPi 2 B:
```
sudo make –f arm_v7_linux.mk all
```

Copy compiled library to your lib directories:

```
sudo cp ../bin/arm_v7-linux/libsnap7.so /usr/lib/libsnap7.so
sudo cp ../bin/arm_v7-linux/libsnap7.so /usr/local/lib/libsnap7.so
```

## Install Python Snap7

```
sudo pip install python-snap7
```


You will need to edit the lib_location on common.py in the /usr/local/lib/python2.7/dist-packages/snap7/ directory
Add a line in the __init__ part of the Snap7Library class:
lib_location='/usr/local/lib/libsnap7.so' 
example below:

```
class Snap7Library(object):
    """
    Snap7 loader and encapsulator. We make this a singleton to make
    sure the library is loaded only once.
    """
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.lib_location = None
            cls._instance.cdll = None
        return cls._instance

    def __init__(self, lib_location=None):
        lib_location='/usr/local/lib/libsnap7.so' # add this line here
        if self.cdll:
            return
        self.lib_location = lib_location or self.lib_location or find_library('snap7')
        if not self.lib_location:
            msg = "can't find snap7 library. If installed, try running ldconfig"
            raise Snap7Exception(msg)
        self.cdll = cdll.LoadLibrary(self.lib_location)

```

Now you can write your client code.
Here's an example on how to connect and read an output Q0.0:

```
from time import sleep
import snap7
from snap7.util import *
import struct

plc = snap7.client.Client()
plc.connect("192.168.12.73",0,1)

area = 0x82    # area for Q memory
start = 0      # location we are going to start the read
length = 1     # length in bytes of the read
bit = 0        # which bit in the Q memory byte we are reading

byte = plc.read_area(area,0,start,length)
print "Q0.0:",get_bool(mbyte,0,bit)
plc.disconnect()
```

# GLPK and pyomo

Install glpk-utils. Not sure if needed (have to try this out).
```
sudo apt-get install glpk-utils 
```

Install python pyomo package:
```
sudo pip install pyomo
```


Now you should be able to run the following example:

Content of transport.py:

```
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Import
from pyomo.environ import *
 
# Creation of a Concrete Model
model = ConcreteModel()
 
## Define sets ##
#  Sets
#       i   canning plants   / seattle, san-diego /
#       j   markets          / new-york, chicago, topeka / ;
model.i = Set(initialize=['seattle','san-diego'], doc='Canning plans')
model.j = Set(initialize=['new-york','chicago', 'topeka'], doc='Markets')
 
## Define parameters ##
#   Parameters
#       a(i)  capacity of plant i in cases
#         /    seattle     350
#              san-diego   600  /
#       b(j)  demand at market j in cases
#         /    new-york    325
#              chicago     300
#              topeka      275  / ;
model.a = Param(model.i, initialize={'seattle':350,'san-diego':600}, doc='Capacity of plant i in cases')
model.b = Param(model.j, initialize={'new-york':325,'chicago':300,'topeka':275}, doc='Demand at market j in cases')
#  Table d(i,j)  distance in thousands of miles
#                    new-york       chicago      topeka
#      seattle          2.5           1.7          1.8
#      san-diego        2.5           1.8          1.4  ;
dtab = {
    ('seattle',  'new-york') : 2.5,
    ('seattle',  'chicago')  : 1.7,
    ('seattle',  'topeka')   : 1.8,
    ('san-diego','new-york') : 2.5,
    ('san-diego','chicago')  : 1.8,
    ('san-diego','topeka')   : 1.4,
    }
model.d = Param(model.i, model.j, initialize=dtab, doc='Distance in thousands of miles')
#  Scalar f  freight in dollars per case per thousand miles  /90/ ;
model.f = Param(initialize=90, doc='Freight in dollars per case per thousand miles')
#  Parameter c(i,j)  transport cost in thousands of dollars per case ;
#            c(i,j) = f * d(i,j) / 1000 ;
def c_init(model, i, j):
  return model.f * model.d[i,j] / 1000
model.c = Param(model.i, model.j, initialize=c_init, doc='Transport cost in thousands of dollar per case')
 
## Define variables ##
#  Variables
#       x(i,j)  shipment quantities in cases
#       z       total transportation costs in thousands of dollars ;
#  Positive Variable x ;
model.x = Var(model.i, model.j, bounds=(0.0,None), doc='Shipment quantities in case')
 
## Define contrains ##
# supply(i)   observe supply limit at plant i
# supply(i) .. sum (j, x(i,j)) =l= a(i)
def supply_rule(model, i):
  return sum(model.x[i,j] for j in model.j) <= model.a[i]
model.supply = Constraint(model.i, rule=supply_rule, doc='Observe supply limit at plant i')
# demand(j)   satisfy demand at market j ;  
# demand(j) .. sum(i, x(i,j)) =g= b(j);
def demand_rule(model, j):
  return sum(model.x[i,j] for i in model.i) >= model.b[j]  
model.demand = Constraint(model.j, rule=demand_rule, doc='Satisfy demand at market j')
 
## Define Objective and solve ##
#  cost        define objective function
#  cost ..        z  =e=  sum((i,j), c(i,j)*x(i,j)) ;
#  Model transport /all/ ;
#  Solve transport using lp minimizing z ;
def objective_rule(model):
  return sum(model.c[i,j]*model.x[i,j] for i in model.i for j in model.j)
model.objective = Objective(rule=objective_rule, sense=minimize, doc='Define objective function')
 
 
## Display of the output ##
# Display x.l, x.m ;
def pyomo_postprocess(options=None, instance=None, results=None):
  model.x.display()
 
# This is an optional code path that allows the script to be run outside of
# pyomo command-line.  For example:  python transport.py
if __name__ == '__main__':
    # This emulates what the pyomo command-line tools does
    from pyomo.opt import SolverFactory
    import pyomo.environ
    opt = SolverFactory("glpk")
    results = opt.solve(model)
    #sends results to stdout
    results.write()
    print("\nDisplaying Solution\n" + '-'*60)
    pyomo_postprocess(None, instance, results)
```

Execute with the following command:

```
pyomo solve --solver=glpk transport.py
```
