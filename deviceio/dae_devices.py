#!/usr/bin/env python3
# encoding: utf-8

import time

from deviceio import deviceio_client

class Parameter:
    def __init__(self, name, value, index=None, durational=None, unit=None, multiplier=None):
        self._name = name
        self._value = value
        self._index = index
        self._durational = durational
        self._unit = unit
        self._multiplier = multiplier

    def hashcode(self):
        if self._index:
            return self._name + "_" + self._index
        else:
            return self._name

    def to_dict(self):
        d = {"name": self._name, "value": self._value}
        if self._index is not None:
            d["index"] = self._index
        if self._durational is not None:
            d["durational"] = self._durational
        if self._unit is not None:
            d["unit"] = self._unit
        if self._multiplier is not None:
            d["multiplier"] = self._multiplier
        return d

class Device:

    def __init__(self, gateway=None):
        self._gateway = gateway

    def flush_measures(self):
        raise NotImplementedError("Should have implemented this")

    def execute_commands(self, commands):
        raise NotImplementedError("Should have implemented this")

    def device_id(self):
        raise NotImplementedError("Should have implemented this")

    def device_type(self):
        raise NotImplementedError("Should have implemented this")


class Gateway(Device):

    def __init__(self):
        super().__init__()
        self._local_storage = {} # Simulate a local storage
        self._local_storage["KEY_ESP_TOKEN"] = "WjnGVpYWX6XLDCcqyfnS2iclM6taNW4VypqXYB4iR0I="

        self._slaves = self._local_storage.get("KEY_SLAVES_DEVICES", {})

        auth_token = self._local_storage.get("KEY_ESP_TOKEN")
        self._http_client = deviceio_client.http_client(self.device_id(), auth_token=auth_token,
                                                        auth_token_callback=self.auth_token_callback,
                                                        commands_callback=self.commands_callback)

    def flush_measures(self):
        pass

    def execute_commands(self, commands):
        print("[WARN] The gateway does not support commands!")

    def pairing(self, device):
        self._slaves[device.device_id] = device
        self.add_device(device)

    def add_device(self, *devices):
        new_devices = []

        for device in devices:
            new_device = {
                "deviceId": device.device_id(),
                "deviceType": device.device_type()
            }
            new_devices.append(new_device)

        self._http_client.send(add_devices=new_devices)

    def send_measures(self, measures):
        self._http_client.send(measures=measures)

    def auth_token_callback(self, auth_token):
        self._local_storage["KEY_ESP_TOKEN"] = auth_token
        print("[DEBUG] The gateway got an auth token:" + str(auth_token))

    def commands_callback(self, commands):
        print("[DEBUG] The gateway got commands: " + str(commands))

        time.sleep(1) # simulated cost of executing the command

        responses = []
        for cmd in commands:
            responses.append({"commandId": cmd["commandId"], "result": 1})

        self._http_client.send(responses=responses)

    def start(self):
        print("[INFO] The gateway \033[91m" + self.device_id() + "\033[0m starting...")

    def device_id(self):
        return "DAE-CALVIN-TEST-4130-001"

    def device_type(self):
        return 4130


class SmartPanelM(Device):
    # DAE Smart Panel SPB-M

    def __init__(self, gateway):
        super().__init__(gateway)
        self._breaker_statuses = {
            "0": "1", # index 0, value 1
            "1": "1",
            "2": "1",
            "3": "1"
        }
        self._updated_measures = {}

    def switch_locally(self, index, on_off):
        if self._breaker_statuses.get(index):
            self._breaker_statuses[index] = on_off

            p = Parameter("breakerStatus", on_off, index)
            self._updated_measures[p.hashcode()] = p

            self.flush_measures()

    def flush_measures(self):
        measures =

        self._gateway.send_measures(measures)

    def execute_commands(self, commands):

        pass

    def device_id(self):
        return "DAE-CALVIN-TEST-4133-001"

    def device_type(self):
        return 4133



if __name__ == "__main__":
    gw = Gateway()
    gw.start()


