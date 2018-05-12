"""
<plugin key="parrot_flower_plugin" name="Parrot Flower Power & Pot sensors" author="tazounet" version="1.0.0" wikilink="https://www.domoticz.com/wiki/Plugins/xxx" externallink="https://github.com/tazounet/parrot_flower_plugin">
    <description>
        This plugin connects to Parrot Flower Power & Pot sensors over Bluetooth LE.
    </description>
    <params>
        <param field="Mode1" label="Device selection" width="300px" required="true">
            <options>
                <option label="Automatic scanning" value="auto" default="true"/>
                <option label="Manual selection (add below)" value="manual"/>
            </options>
        </param>
        <param field="Mode2" label="Devices mac adresses, capitalised and comma separated" width="300px" required="false" default=""/>
        <param field="Mode3" label="Backend selection" width="300px" required="true">
            <options>
                <option label="gatttool" value="gatttool" default="true"/>
                <option label="bluepy" value="bluepy"/>
                <option label="pygatt" value="pygatt"/>
            </options>
        </param>
        <param field="Mode4" label="Polling interval (minutes, 30 mini)" width="40px" required="true" default="60"/>
    </params>
</plugin>
"""

bluepyError = 0

try:
    import Domoticz
except ImportError:
    import fakeDomoticz as Domoticz
import time
import sys
sys.path.append("/usr/local/lib/python3.5/dist-packages")
import shelve
import os
from datetime import datetime
from datetime import timedelta
from parrot_flower import parrot_flower_scanner
import parrot_flower
try:
    from parrot_flower.parrot_flower_poller import ParrotFlowerPoller, \
        P_CONDUCTIVITY, P_MOISTURE, P_LIGHT, P_TEMPERATURE, P_BATTERY
except:
    bluepyError = 1
try:
    from btlewrap import GatttoolBackend, BluepyBackend, PygattBackend
except:
    bluepyError = 1

class BasePlugin:

    def __init__(self):
        self.macs = []
        self.backend = GatttoolBackend
        self.currentlyPolling = 255
        self.nextupdate = datetime.now()
        self.pollinterval = 60  # default polling interval in minutes
        return


    def onStart(self):
        #Domoticz.Debugging(1)

        if bluepyError == 1:
            Domoticz.Error("Error loading Parrot Flower libraries")

        Domoticz.Debug("Parrot Flower - devices made so far (max 255): " + str(len(Devices)))

        # get the mac addresses of the sensors
        if Parameters["Mode1"] == 'auto':
            Domoticz.Log("Automatic mode is selected")
            self.floraScan()
        else:
            Domoticz.Log("Manual mode is selected")
            self.macs = parseCSV(Parameters["Mode2"])
            self.createSensors()
        #Domoticz.Log("macs = {}".format(self.macs))

        # get the backend
        if Parameters["Mode3"] == 'gatttool':
            self.backend = GatttoolBackend
        elif Parameters["Mode3"] == 'bluepy':
            self.backend = BluepyBackend
        elif Parameters["Mode3"] == 'pygatt':
            self.backend = PygattBackend

        # check polling interval parameter
        try:
            temp = int(Parameters["Mode4"])
        except:
            Domoticz.Error("Invalid polling interval parameter")
        else:
            if temp < 30:
                temp = 30  # minimum polling interval
                Domoticz.Error("Specified polling interval too short: changed to 30 minutes")
            elif temp > 1440:
                temp = 1440  # maximum polling interval is 1 day
                Domoticz.Error("Specified polling interval too long: changed to 1440 minutes (24 hours)")
            self.pollinterval = temp
        Domoticz.Log("Using polling interval of {} minutes".format(str(self.pollinterval)))


    def onStop(self):
        Domoticz.Log("onStop called")


    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")


    def onMessage(self, Connection, Data, Status, Extra):
        Domoticz.Log("onMessage called")


    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))


    def onHeartbeat(self):
        now = datetime.now()
        if now >= self.nextupdate:
            self.nextupdate = now + timedelta(minutes=self.pollinterval)
            #By setting this to 0, the polling function will run.
            self.currentlyPolling = 0

        # for now this uses the shelve database as its source of truth.
        if (self.currentlyPolling < len(self.macs)):
            try:
                self.getPlantData(int(self.currentlyPolling))
            except:
                Domoticz.Error("Can't get data from sensor " + str(self.macs[self.currentlyPolling]))
            self.currentlyPolling = self.currentlyPolling + 1


    # function to create corresponding sensors in Domoticz if there are Parrot Flower which don't have them yet.
    def createSensors(self):
        # create the domoticz sensors if necessary
        if (len(Devices) / 4) < len(self.macs):
            Domoticz.Debug("Creating new sensors")
            # Create the sensors. Later we get the data.
            for idx, mac in enumerate(self.macs):
                Domoticz.Debug("Creating new sensors for Parrot Flower Power & Pot at " + str(mac))
                sensorBaseName = "#" + str(idx) + " "

                sensorNumber = (idx * 4) + 1
                if sensorNumber not in Devices:

                    #moisture
                    sensorName = sensorBaseName + "Moisture"
                    Domoticz.Debug("Creating first sensor, #" + str(sensorNumber))
                    Domoticz.Debug("Creating first sensor, name: " + str(sensorName))
                    Domoticz.Device(Name=sensorName, Unit=sensorNumber, TypeName="Percentage", Used=1).Create()
                    Domoticz.Log("Created device: " + sensorName)

                    #temperature
                    sensorNumber = (idx * 4) + 2
                    sensorName = sensorBaseName + "Temperature"
                    Domoticz.Device(Name=sensorName, Unit=sensorNumber, TypeName="Temperature", Used=1).Create()
                    Domoticz.Log("Created device: " + sensorName)

                    #light
                    sensorNumber = (idx * 4) + 3
                    sensorName = sensorBaseName + "Light"
                    Domoticz.Device(Name=sensorName, Unit=sensorNumber, TypeName="Illumination", Used=1).Create()
                    Domoticz.Log("Created device: " + sensorName)

                    #fertility
                    sensorNumber = (idx * 4) + 4
                    sensorName = sensorBaseName + "Conductivity"
                    Domoticz.Device(Name=sensorName, Unit=sensorNumber, TypeName="Custom", Used=1).Create()
                    Domoticz.Log("Created device: " + sensorName)


    # function to poll a Flower Mate for its data
    def getPlantData(self, idx):
        #for idx, mac in enumerate(self.macs):
        mac = self.macs[idx]
        Domoticz.Log("Getting data from sensor: " + str(mac))
        poller = ParrotFlowerPoller(str(mac), self.backend)

        val_bat  = int("{}".format(poller.parameter_value(P_BATTERY)))
        nValue = 0

        #moisture
        sensorNumber1 = (idx * 4) + 1
        val_moist = "{}".format(poller.parameter_value(P_MOISTURE))
        Devices[sensorNumber1].Update(nValue=nValue, sValue=val_moist, BatteryLevel=val_bat)
        Domoticz.Log("moisture = " + str(val_moist))

        #temperature
        sensorNumber2 = (idx * 4) + 2
        val_temp = "{}".format(poller.parameter_value(P_TEMPERATURE))
        Devices[sensorNumber2].Update(nValue=nValue, sValue=val_temp, BatteryLevel=val_bat)
        Domoticz.Log("temperature = " + str(val_temp))

        #light
        sensorNumber3 = (idx * 4) + 3
        val_lux = "{}".format(poller.parameter_value(P_LIGHT))
        Devices[sensorNumber3].Update(nValue=nValue, sValue=val_lux, BatteryLevel=val_bat)
        Domoticz.Log("light = " + str(val_lux))

        #fertility
        sensorNumber4 = (idx * 4) + 4
        val_cond = "{}".format(poller.parameter_value(P_CONDUCTIVITY))
        Devices[sensorNumber4].Update(nValue=nValue, sValue=val_cond, BatteryLevel=val_bat)
        Domoticz.Log("conductivity = " + str(val_cond))


    # function to scan for devices, and store and compare the outcome
    def floraScan(self):
        Domoticz.Log("Scanning for Parrot Flower Power & Pot sensors")

        #databaseFile=os.path.join(os.environ['HOME'],'ParrotFlower')
        # first, let's get the list of devices we already know about
        database = shelve.open('ParrotFlower')

        try:
            knownSensors = database['macs']
            oldLength = len(knownSensors)
            Domoticz.Debug("Already know something:" + str(oldLength))
            Domoticz.Log("Already known devices:" + str(knownSensors))
        except:
            knownSensors = []
            database['macs'] = knownSensors
            oldLength = 0;
            Domoticz.Debug("No existing sensors in system?")

        #Next we scan to look for new sensors
        try:
            foundParrots = parrot_flower_scanner.scan(self.backend, 5)
            Domoticz.Log("Number of devices found via bluetooth scan = " + str(len(foundParrots)))
        except:
            foundParrots = []
            Domoticz.Log("Scan failed")

        for sensor in foundParrots:
            if sensor not in knownSensors:
                knownSensors.append(str(sensor))
                Domoticz.Log("Found new device: " + str(sensor))

        if len(knownSensors) != oldLength:
            database['macs'] = knownSensors
            Domoticz.Log("Updating database")

        database.close()

        self.macs = knownSensors
        self.createSensors()


global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


def parseCSV(strCSV):
    listvals = []
    for value in strCSV.split(","):
        listvals.append(value)
    return listvals

