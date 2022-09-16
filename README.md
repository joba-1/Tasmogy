# Tasmogy - Energy Monitoring Gateway from Tasmota to Influx DB

This is a python script querying energy readings from a tasmota device.

The readings are transfered into an influx database.

It is also possible to operate a tasmota switch to toggle a fan on and off driven by power consumption.

The script is used by a systemd service so the script does its job whenever the server is up

## Install

* copy tasmogy.py and tasmogy.sh to ~/bin
* copy tasmogy.service to /etc/systemd/system
* adapt username and hostname of energy device in service file (and optionally the hostname of a fan power switch)
* create conda environment "tasmogy" with python, requests and paho-mqtt
* create influx database "energies"
* start service as root / with sudo
```
systemctl daemon-reload
systemctl enable tasmogy
systemctl start tasmogy
```
## Use

As soon as tasmota device has energy readings with ApparentPower != 0.0 it will create entries in influx db measurement "energy".
A fan can be switched on during high power (see tasmogy.py for power limits and delays).

Use influx data for, e.g. a grafana dashboard

![image](https://user-images.githubusercontent.com/32450554/190662381-3c4e99fe-26fd-481c-9ef0-5e2d18530ff5.png)
