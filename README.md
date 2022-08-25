# Tasmogy - Energy Monitoring Tasmota to Influx Gateway

## Install

* copy tasmogy.py and tasmogy.sh to ~/bin
* copy tasmogy.service to /etc/systemd/system
* adapt username and hostname of tasmota device in service file
* create conda environment with python, requests and paho-mqtt
* create influx database energies
* start service
	systemctl daemon-reload
	systemctl enable tasmogy
	systemctl start tasmogy

As soon as tasmota device has energy readings with ApparentPower != 0.0 it will create entries in influx db measurement energy

Use it for, e.g. grafana dashboard
