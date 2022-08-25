"""
Read energy values from syslog of a tasmota device
Put result in influx db if ApparentPower != 0.0

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
    energy = data["ENERGY"]
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
        return False
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