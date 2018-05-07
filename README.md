# Parrot Flower Power & Pot plugin

## Installation
Install the plugin in Domoticz: https://www.domoticz.com/wiki/Using_Python_plugins

Install dependencies:
  pip3 install bluepy
  pip3 install btlewrap

In automatic mode, the plugin will do bluetooth scans at startup, and integrate any Parrot Flower devices it finds. 

In manual mode you can select which devices to add by entering their mac addresses on the hardware page. To find your Parrot Flower' mac-addresses do a bluetooth scan:

  sudo hcitool lescan

## Thanks to

https://github.com/flatsiedatsie/Mi_Flower_mate_plugin
https://github.com/open-homeautomation/miflora
https://github.com/ChristianKuehnel/btlewrap
https://github.com/afer92/node-flower-power
