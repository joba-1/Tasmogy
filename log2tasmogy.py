"""
Read energy values from stdin
Puts result in influx db if ApparentPower != 0.0
Input must be syslog lines of a tasmota device with format "timestamp device ... json_without_spaces"
json must have entry StatusSNS/ENERGY

2022-09-16T11:50:00.037916+02:00 nous1 ESP-MQT: stat/nous1/STATUS10 = {"StatusSNS":{"Time":"2022-09-16T10:50:00","ENERGY":{"TotalStartTime":"2022-08-17T13:15:49","Total":36.8569,"Yesterday":0.5030,"Today":0.0573,"Power":35.6,"ApparentPower":47.6,"ReactivePower":31.6,"Factor":0.75,"Voltage":229,"Current":0.208}}}

requires requests, python-dateutil (pip)
"""

import sys
import json
import requests
from dateutil.parser import isoparse

influx_host = "job4"

influx_db = "energies"
influx_measurements = "energy"

influx_url = f"http://{influx_host}:8086/write?db={influx_db}"


def process_line(line, nr):
    global no_power
    tokens = line.split(maxsplit=5)
    data_epoch_ns = int(isoparse(tokens[0]).timestamp()*1000000000)
    tasmota_device = tokens[1]

    try:
        data = json.loads(tokens[-1])
    except Exception as e:
        print(f"Exception {e} for '{tokens[-1]}'")
        return False  # invalid json

    try:
        # STATUS10 message
        energy = data["StatusSNS"]["ENERGY"]
    except KeyError:
        try:
            # SENSOR message
            energy = data["ENERGY"]
        except KeyError:
            print(f"Key Error for '{data}'")
            return False  # not an energy reading

    payload = f"{influx_measurements},device={tasmota_device}"
    sep=" "
    for key, value in energy.items():
        if key == "ApparentPower":
            if value == 0.0:
                if no_power:
                    return False
                else:
                    no_power = True
            else:
                no_power = False
        if type(value) == type(""):
            value = f'"{value}"'
        payload += f"{sep}{key}={value}"
        sep=","
    payload += f" {data_epoch_ns}"

    response = requests.post(url=influx_url, data=payload)
    if response.status_code < 200 or response.status_code > 299:
        print(f"line {nr}: code {response.status_code} for '{response.text}' with '{payload}'")
        return False  # not inserted

    return True


if __name__ == "__main__":
    print("Reading syslog entries of tasmota energy device and insert into influx db")
    no_power = False
    line_count = 0
    insert_count = 0

    for line in sys.stdin:
        line_count += 1
        if process_line(line, line_count):
            insert_count += 1

    print(f"Inserted {insert_count} of {line_count} lines into {influx_db}.{influx_measurements}@{influx_host}")

