#!/usr/bin/env python
# -*- coding: utf-8 -*-

# start with following command in terminal: pyomo solve --solver=glpk ./scheduling.py

# Import
import numpy as np
import platform
import matplotlib.pyplot as plt
from pyomo.environ import *
from pyomo.core import Var
import xlwt

#=====================================================================================
# Input data
## Thermal demand in W
time = np.array([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24])
demandThermal = np.array([4021.85,4054.65,4057.08,4040.75,4019.74,3987.02,3968.28,3969.74,
                          3965.96,3871.5,3817.4,3773.91,3623.16,3498.71,3488.95,3578.58,
                          3783.95,3823.33,3870.06,3905.22,3907.65,3895.94,3902.9,3879.62])

## Electricity price in €/kWh
price = np.array([0.0558, 0.0548, 0.0499, 0.0479, 0.0486, 0.0522, 0.0655, 0.0920, 
                  0.1138, 0.1134, 0.1175, 0.1265, 0.1260, 0.1315, 0.1347, 0.1363, 
                  0.1297, 0.1137, 0.1095, 0.1034, 0.0817, 0.0750, 0.0816, 0.0700])

Qdot_heater = 5000 # Nominal thermal power of heater
Q_storage_cap = 40000000 # Storage capacity in Ws
P_heater = -2000 # Nominal electricl power of heater; <0: generator
TimeStep = 3600 # Length of time intervals; e.g. 1 hour: 3600s
SoC_min = 0 # Minimum allowed State of Charge (SoC)
SoC_max = 1 # Maximum allowed State of Charge (SoC)
SoC_ini = 0.5 # Initial State of Charge (SoC)

#=====================================================================================
# Methods for parameter and variable initialization

# Init of thermal demand
def init_thermaldemand(model, i):
  return float(demandThermal[i-1])

# Init of electricity price
def init_prices(model, i):
  return float(price[i-1])

#=====================================================================================
# Create Abstract Model
model = AbstractModel()

# Scheduling Horizon
model.T = Set(initialize=range(1,25)) # values: 1..24
model.T0 = Set(initialize=range(0,25)) # values: 0..24

# Parameters
model.qdmnd = Param(model.T, initialize=init_thermaldemand, doc="Thermal demand")
model.pricegrid = Param(model.T, initialize=init_prices, doc="Electricity price")
model.qheater = Param(initialize=Qdot_heater, doc="Nominal thermal power of heater in W")
model.QstrgCap = Param(initialize=Q_storage_cap, doc="Storage capacity in Ws")
model.pheater = Param(initialize=P_heater, doc="Nominal electrical power of heater in W")
model.dt = Param(initialize=TimeStep, doc="time constant")
model.SoCmin = Param(initialize=SoC_min, doc="Minimum SoC of storage")
model.SoCmax = Param(initialize=SoC_max, doc="Maximum SoC of storage")

# Variables
model.modlvl = Var(model.T, initialize=0, domain=Binary, doc="Modulation level") # domain=Binary, NonNegativeReals ; bounds=(0,6)
model.qstrg = Var(model.T, initialize=0, doc="Power flow storage")
model.Qstrg = Var(model.T0, initialize=SoC_ini*Q_storage_cap, doc="Energy in storage")
model.pgrid = Var(model.T, initialize=0, doc="Power export to electrical grid")

# Constraints
# Contraint thermal energy balance system
def cnstrThermalBalance(model, t):
  return (-model.qdmnd[t] == -model.modlvl[t] * model.qheater + model.qstrg[t])

# Contraint thermal energy balance storage
def cnstrStorageBalance(model, t):
  return (model.Qstrg[t] == model.Qstrg[t-1] + model.qstrg[t] * model.dt)

# Constarint State of Charge (SoC) of storage
def cnstrSoC(model, t):
  # return the expression for the constraint for i
  return (model.SoCmin <= model.Qstrg[t]/model.QstrgCap <= model.SoCmax)

# Expression grid export/import
def cnstrGrid(model, t):
  # return the expression for the constraint for i
  return (model.pheater * model.modlvl[t] == model.pgrid[t])

# Expression objective function
def obj_expression(model):
  return sum(model.pgrid[t] * model.pricegrid[t] for t in model.T)

# Set objective function
model.obj = Objective(rule=obj_expression, sense=minimize)

# Add constraints to model
model.CnstrThermalBalance = Constraint(model.T, rule=cnstrThermalBalance)
model.CnstrStorageBalance = Constraint(model.T, rule=cnstrStorageBalance)
model.CnstrSoC = Constraint(model.T, rule=cnstrSoC)
model.CnstrGrid = Constraint(model.T, rule=cnstrGrid)

#=====================================================================================
# Postprocessing

# Read values of model variables and return list with values
def readVarValues(var_name, instance):
  listReturn = []
  for v in instance.component_objects(Var, active=True):
    #print("Variable", v)
    if str(v) == str(var_name):
      varobject = getattr(instance, str(v))
      for index in varobject:
        #print(varobject[index].value)
        listReturn.append(varobject[index].value)
  return listReturn

# Pyomo postprocessing. Called by pyomo after solving
def pyomo_postprocess(options=None, instance=None, results=None):
  # Print python version
  print(platform.python_version())

  modlvl = readVarValues("modlvl", instance)
  Qstrg = readVarValues("Qstrg", instance)
  PGrid = readVarValues("pgrid", instance)

  width = 4 # in inches
  height = 4 # in inches
  
  # Plot the data
  fig, ax = plt.subplots(dpi=500, nrows=5, ncols=1, sharex=True, sharey=False) # figsize=(width, height)
  plot1 = ax[0].step(time, price, color='#0072B2')
  plot2 = ax[1].step(time, modlvl, color='#0072B2')
  plot3 = ax[2].step(time, Qstrg[1:], color='#0072B2')
  plot4 = ax[3].step(time, PGrid, color='#0072B2')
  plot5 = ax[4].step(time, demandThermal, color='#0072B2')

  ax[0].set_xlim(time[0], time[23])
  ax[1].set_ylim(-0.1, 1.1)
  ax[3].set_ylim(min(PGrid)*1.1, max(PGrid)*1.1)

  ax[4].set_xlabel("Time in hours")
  ax[0].set_ylabel("Price in \n €/MWh")
  ax[1].set_ylabel("Modulation \n level")
  ax[2].set_ylabel("Stored energy \n in Ws")
  ax[3].set_ylabel("P Grid \n in W")
  ax[4].set_ylabel("Thermal demand")

  fig.subplots_adjust(left=0.14, right=0.98, top=0.98, hspace=0.05, wspace=0.02)

  fig.savefig("schedule.pdf")

  # Export data to Excel workbook
  book = xlwt.Workbook()

  sheet1 = book.add_sheet('Sheet 1')

  sheet1.write(0, 0, "Price in ct/kWh")
  sheet1.write(0, 1, "Modulation level")
  sheet1.write(0, 2, "Stored energy in Ws")
  sheet1.write(0, 3, "Grid feed-in in W")
  sheet1.write(0, 4, "Thermal demand in W")

  for i in range(len(price)):
    sheet1.write(i+1, 0, price[i])
    sheet1.write(i+1, 1, modlvl[i])
    sheet1.write(i+1, 2, Qstrg[i+1])
    sheet1.write(i+1, 3, PGrid[i])
    sheet1.write(i+1, 4, demandThermal[i])

  book.save('data.xls')

#=====================================================================================
# This is an optional code path that allows the script to be run outside of
# pyomo command-line.  For example:  python transport.py
if __name__ == '__main__':
  print("Python version: ", platform.python_version())
  # This emulates what the pyomo command-line tools does
  from pyomo.opt import SolverFactory
  import pyomo.environ
  opt = SolverFactory("glpk")
  instance = model.create()
  results = opt.solve(instance)
  #sends results to stdout
  results.write()
  print("\nDisplaying Solution\n" + '-'*60)
  pyomo_postprocess(None, instance, results)
