"""
Request energy values from a tasmota device in regular intervals via mqtt
Put result in influx db if ApparentPower != 0.0
Optional:
Switch fan on if power is above upper limit for some time
Switch fan off if power is below lower limit for some time

requires requests, paho-mqtt

Author: Joachim Banzhaf
License: GPL V2
"""

from threading import Timer
import sys
import json
import requests
import paho.mqtt.client as mqtt
from datetime import datetime as dt


mqtt_broker = "job4"
influx_host = "job4"

request_interval = 2  # s

influx_db = "energies"
influx_measurements = "energy"

influx_url = f"http://{influx_host}:8086/write?db={influx_db}"

high_power = 250  # W
low_power = 150   # W
on_delay = 120    # s
off_delay = 360   # s


class RepeatTimer(Timer):
    """ Timer that is called repeatedly
    """
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class FanSwitch:
    """ Delay fan switch if over high_limit or below low_limit (debounce)
    """
    def __init__(self, high_limit, low_limit, on_delay, off_delay):
        self.delay_since = None  # datetime since beyond high or low limit
        self.delay_high = None   # beyond high or low limit
        self.fan_power = None    # fan power according to mqtt
        self.high_limit = high_limit
        self.low_limit = low_limit
        self.on_delay = on_delay
        self.off_delay = off_delay

    def handle_power(self, power):
        if power > self.high_limit and self.delay_high != True:
                self.delay_high = True
                if self.fan_power != self.delay_high:
                    self.delay_since = dt.now()
                    self.switch_delay = self.on_delay
                    print(f"delay {self.on_delay}s switch fan ON")
                else:
                    self.delay_since = None
                    print(f"fan already ON")
        elif power < self.low_limit and self.delay_high != False:
                self.delay_high = False
                if self.fan_power != self.delay_high:
                    self.delay_since = dt.now()
                    self.switch_delay = self.off_delay
                    print(f"delay {self.off_delay}s switch fan OFF")
                else:
                    self.delay_since = None
                    print(f"fan already OFF")

        if self.delay_since is not None:
            if (dt.now() - self.delay_since).total_seconds() > self.switch_delay:
                self.delay_since = None
                if self.fan_power != self.delay_high:
                    print(f"switch fan power {self.fan_power} -> {self.delay_high}")
                    if self.delay_high:
                        cmd = "ON"
                    else:
                        cmd = "OFF"
                    mqtt_client.publish(mqtt_fan_command, cmd)  # set fan power
                    self.fan_power = self.delay_high
                else:
                    print(f"keep fan power {self.fan_power}")

    def fan_state(self, state):
        if self.fan_power != state:
            self.fan_power = state
            print(f"got fan power {self.fan_power}")


def on_connect(mqtt_client, userdata, flags, rc):
    print(f"connected to mqtt broker {mqtt_broker} with result code {rc}")
    mqtt_client.subscribe(mqtt_response_topic)  # wait for sensor status
    if fanSwitch is not None:
        mqtt_client.subscribe(mqtt_fan_state)       # wait for fan status
        mqtt_client.publish(mqtt_fan_command, "")   # query fan status


def on_message(mqtt_client, userdata, msg):
    try:
        if fanSwitch is not None and msg.topic == mqtt_fan_state:
            # message is a fan status
            payload = msg.payload.decode("utf-8")
            fanSwitch.fan_state(payload == "ON")
            return

        # message is a sensor status
        data = json.loads(msg.payload.decode("utf-8"))
        energy = data["StatusSNS"]["ENERGY"]
        payload = f"{influx_measurements},device={power_device}"
        sep=" " 
        global no_power
        power = None
        for key, value in energy.items():
            if key == "ApparentPower":
                if value == 0.0:
                    if no_power:
                        return
                    else:
                        no_power = True
                else:
                    no_power = False
            elif key == "Power":
                power = int(value)
            if type(value) == type(""):
                value = f'"{value}"'
            payload += f"{sep}{key}={value}"
            sep=","

        response = requests.post(url=influx_url, data=payload)
        if response.status_code < 200 or response.status_code > 299:
            print(f"influx {influx_host} code {response.status_code} for '{response.text}' with '{payload}'")

        if power is not None and fanSwitch is not None:
            fanSwitch.handle_power(power)
    except UnicodeDecodeError:
        pass  # not interested...
    

def mqtt_request():
    mqtt_client.publish(mqtt_request_topic, mqtt_request_message)


if __name__ == "__main__":
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print(f"syntax: {sys.argv[0]} power_device [fan_device]")
        exit(1)

    power_device = sys.argv[1]
    mqtt_request_topic = f"cmnd/{power_device}/STATUS"
    mqtt_request_message = "10"

    mqtt_response_topic = f"stat/{power_device}/STATUS10"

    if len(sys.argv) == 3:
        fan_device = sys.argv[2]
        print(f"start monitor for {power_device} with fan {fan_device}")
        mqtt_fan_command = f"cmnd/{fan_device}/POWER"
        mqtt_fan_state = f"stat/{fan_device}/POWER"
        fanSwitch = FanSwitch(high_power, low_power, on_delay, off_delay)
    else:
        print(f"start monitor for {power_device} without fan")
        fanSwitch = None

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
