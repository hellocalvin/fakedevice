#!/usr/bin/env python3
# encoding: utf-8

from queue import Queue
from threading import Thread
from threading import Lock

import json
import requests
import traceback
import sys


class DeviceIOClient:
    def __init__(self, proxy_id, auth_token=None, auth_token_callback=None, commands_callback=None):
        self._host = "https://sboxall.presencepro.com:8443/deviceio"
        self._measure_queue = Queue(10)
        self._command_queue = Queue(10)
        self._seq_gen = (x for x in range(10000, 100000))
        self._seq_lock = Lock()

        self._proxy_id = proxy_id
        self._auth_token = auth_token
        self._auth_token_callback = auth_token_callback
        self._commands_callback = commands_callback

    def _start_measures_listener(self):
        """ receiving measures/responses from a gateway and send them to deviceio """
        raise NotImplementedError("Should have implemented this")

    def _start_commands_listener(self, callback):
        """ receiving commands from deviceio and invoking commands callback"""
        raise NotImplementedError("Should have implemented this")

    def _check_device_status(self):
        headers = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["PPCAuthorization"] = "esp token=" + self._auth_token

        content = {
            "proxyId": self._proxy_id,
            "seq": self._next_seq()
        }

        r = requests.post(self._host + "/mljson", headers=headers, data=json.dumps(content))

        j = json.loads(r.text)
        if j.get("status") == "UNAUTHORIZED":

            auth_token = j.get("authToken")
            if auth_token:
                print("[INFO] Got a new auth token! Should store it and replace the existing one!")
                self._auth_token = auth_token

                if self._auth_token_callback:
                    self._auth_token_callback(auth_token)
                return True
            else:
                print("[ERROR] The auth token is wrong!")
                return False

        elif j.get("status") == "UNKNOWN":
            # not registered
            print("Not registered!")
            return False
        else:
            return True

    def _next_seq(self):
        self._seq_lock.acquire()
        try:
            return next(self._seq_gen)
        except StopIteration:
            self._seq_gen = (x for x in range(10000, 100000))
            return next(self._seq_gen)
        finally:
            self._seq_lock.release()

    def send(self, measures=None, add_devices=None, responses=None, alerts=None):
        """sends data to deviceio.

            :param measures: (optional) List, list of measured data objects
            :param add_devices: (optional) List, list of device definitions
            :param responses: (optional) List, list of command responses
            :param alerts: (optional) List, list of  device alerts
            """
        if measures or add_devices or responses or alerts:
            content = {
                "proxyId": self._proxy_id,
                "seq": self._next_seq()
            }

            if measures:
                content["measures"] = measures
            if add_devices:
                content["addDevices"] = add_devices
            if responses:
                content["responses"] = responses
            if alerts:
                content["alerts"] = alerts

            self._measure_queue.put(content)

    def start(self):
        if not self._check_device_status():
            print("[ERROR] The device is unavailable!")
            return False

        if self._commands_callback:
            self._start_commands_listener(self._commands_callback)
        else:
            print("[WARN] The device does not support receiving commands!")

        self._start_measures_listener()
        print("[INFO] The device can send measures from now!")

        return True

    def check_availability(self):
        """ check for cloud availability """
        r = requests.get(self._host + "/watch")
        if r.text is not None and r.text == "OK":
            return True
        return False


class HttpClient(DeviceIOClient):

    def __init__(self, proxy_id, auth_token=None, auth_token_callback=None, commands_callback=None):
        super().__init__(proxy_id, auth_token, auth_token_callback, commands_callback)
        self._http_host = self._host + "/mljson"

    def _build_http_headers(self):
        headers = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["PPCAuthorization"] = "esp token=" + self._auth_token
        return headers

    def _start_measures_listener(self):
        def run():
            while True:
                content = self._measure_queue.get()
                print("[DEBUG] HTTP POST: " + str(content))

                r = requests.post(self._http_host, headers=self._build_http_headers(), data=json.dumps(content))
                j = json.loads(r.text)
                print("[DEBUG] HTTP POST RETURN: " + str(j))

        Thread(target=run).start()

    def _start_commands_listener(self, callback):

        def ack_commands(commands):
            responses = []
            for cmd in commands:
                responses.append({"commandId": cmd["commandId"], "result": "0"})

            self.send(responses=responses)

        def run():
            while True:
                try:
                    params = {"id": self._proxy_id, "timeout": 60}

                    r = requests.get(self._http_host, headers=self._build_http_headers(), params=params)
                    if r.text is not None and r.text != "":
                        j = json.loads(r.text)
                        print("[DEBUG] HTTP GET: " + str(j))

                        commands = j["commands"]
                        ack_commands(commands)
                        callback(commands)
                    else:
                        print("[DEBUG] 60s timeout")
                except:
                    s = traceback.format_exc()
                    sys.stderr.write(s + "\n\n")

        Thread(target=run).start()


def http_client(proxy_id, auth_token, auth_token_callback, commands_callback):
    hc = HttpClient(proxy_id, auth_token, auth_token_callback, commands_callback)
    hc.start()
    return hc







