"""
Request energy values from a tasmota device in regular intervals via mqtt
Put result in influx db if ApparentPower != 0.0

requires requests, paho-mqtt
"""

from threading import Timer
import sys
import json
import requests
import paho.mqtt.client as mqtt


mqtt_broker = "job4"
influx_host = "job4"

request_interval = 2  # s

influx_db = "energies"
influx_measurements = "energy"

influx_url = f"http://{influx_host}:8086/write?db={influx_db}"


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

def on_connect(mqtt_client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    mqtt_client.subscribe(mqtt_response_topic)

def on_message(mqtt_client, userdata, msg):
    data = json.loads(msg.payload.decode("utf-8"))
    energy = data["StatusSNS"]["ENERGY"]
    payload = f"{influx_measurements},device={tasmota_device}"
    sep=" "
    global no_power
    for key, value in energy.items():
        if key == "ApparentPower":
            if value == 0.0:
                if no_power:
                    return
                else:
                    no_power = True
            else:
                no_power = False
        if type(value) == type(""):
            value = f'"{value}"'
        payload += f"{sep}{key}={value}"
        sep=","
    response = requests.post(url=influx_url, data=payload)
    if response.status_code < 200 or response.status_code > 299:
        print(f"code {response.status_code} for '{response.text}' with '{payload}'")

def mqtt_request():
    mqtt_client.publish(mqtt_request_topic, mqtt_request_message)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"syntax: {sys.argv[0]} tasmota_device")
        exit(1)

    tasmota_device = sys.argv[1]
    mqtt_request_topic = f"cmnd/{tasmota_device}/STATUS"
    mqtt_request_message = "10"

    mqtt_response_topic = f"stat/{tasmota_device}/STATUS10"

    no_power = False

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_broker)

    timer = RepeatTimer(request_interval, mqtt_request)
    timer.start()

    try:
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        timer.cancel()

    print("bye")
