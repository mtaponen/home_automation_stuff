# Home Automation Stuff
Misc collection of home automation configs and sources

Setup:
- HomeAssistant running in Raspberry PI using Docker
- ghcr.io/home-assistant/home-assistant:stable - image
- Configs & data on NAS mount

Extra interfaces / components
- HACS: Luxtronic for Alpha Innotec ground-heat-pump control (MLP = Ground Heat Pump)
- MelCloud for Mitsubishi air-heat-pump control (ILP = Air Heat Pump)
- Tuya SmartLife for Wifi Wallplugs and thermostats
- MQTT for energy measurement (generic ESP8266 board with LDR hot-glued to the meter), Mosquitto installed on RPi
- Spot-hinta-API from https://spot-hinta.fi/ for electricity price info
- Google calendar for heating control

Comments and namings in Finnish -use ChatGPT for translation if needed- checked and seems to work ok-ish

License - Something MIT like. Use if you find this useful. YMMV, Caveat Emptor, use with your own responsibility and no warranty.
  

