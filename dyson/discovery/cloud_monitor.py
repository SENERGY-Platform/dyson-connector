"""
   Copyright 2020 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from ..configuration import config
from ..logger import root_logger
from ..device_manager import DeviceManager
from ..types.device import device_type_map
import time, requests, cc_lib
from threading import Thread


logger = root_logger.getChild(__name__.split(".", 1)[-1])


def getApiCredentials():
    body = {
        "Email": config.Account.email,
        "Password": config.Account.pw
    }
    http_resp = requests.post(
        url="https://{}/{}{}".format(config.Cloud.host, config.Cloud.auth_endpt, config.Account.country),
        json=body,
        verify=False
    )
    if http_resp.status_code == 200:
        credentials = http_resp.json()
        config.Cloud.user = credentials.get('Account')
        config.Cloud.pw = credentials.get('Password')
        return True
    logger.error(
        "could not retrieve dyson cloud credentials - '{}' - '{}'".format(http_resp.status_code, http_resp.raw))
    return False


def apiQueryDevices():
    unknown_devices = dict()
    http_resp = requests.get(
        url="https://{}/{}".format(config.Cloud.host, config.Cloud.provisioning_endpt),
        auth=(config.Cloud.user, config.Cloud.pw),
        verify=False
    )
    if http_resp.status_code == 200:
        devices = http_resp.json()
        for device in devices:
            try:
                unknown_devices[device['Serial']] = (
                    {
                        "name": device["Name"]
                    },
                    {
                        "type": device["ProductType"],
                        "pw": device["LocalCredentials"]
                    }
                )
            except KeyError:
                logger.error("missing device serial or malformed message - '{}'".format(device))
    return unknown_devices


def diff(known, unknown):
    known_set = set(known)
    unknown_set = set(unknown)
    missing = known_set - unknown_set
    new = unknown_set - known_set
    changed = {key for key in known_set & unknown_set if dict(known[key]) != unknown[key][0]}
    return missing, new, changed


class CloudMonitor(Thread):
    def __init__(self, device_manager: DeviceManager, client: cc_lib.client.Client):
        super().__init__(name=__class__.__name__, daemon=True)
        self.__device_manager = device_manager
        self.__client = client

    def run(self):
        if not (config.Cloud.user and config.Cloud.pw):
            while not getApiCredentials():
                logger.info("retry in 30s")
                time.sleep(30)
        while True:
            unknown_devices = apiQueryDevices()
            self.__evaluate(unknown_devices)
            time.sleep(config.Cloud.poll_interval)

    def __evaluate(self, queried_devices):
        missing_devices, new_devices, changed_devices = diff(self.__device_manager.devices, queried_devices)
        if missing_devices:
            futures = list()
            for device_id in missing_devices:
                logger.info("can't find '{}'".format(device_id))
                futures.append((device_id, self.__client.deleteDevice(device_id, asynchronous=True)))
            for device_id, future in futures:
                future.wait()
                try:
                    future.result()
                    self.__device_manager.delete(device_id)
                except cc_lib.client.DeviceDeleteError:
                    pass
        if new_devices:
            futures = list()
            for device_id in new_devices:
                logger.info("found '{}' with id '{}'".format(queried_devices[device_id][0]["name"], device_id))
                device = device_type_map[queried_devices[device_id][1]["type"]](device_id, queried_devices[device_id][1]["pw"], **queried_devices[device_id][0])
                futures.append((device, self.__client.addDevice(device, asynchronous=True)))
            for device, future in futures:
                future.wait()
                try:
                    future.result()
                    self.__device_manager.add(device)
                except (cc_lib.client.DeviceAddError, cc_lib.client.DeviceUpdateError):
                    pass
        if changed_devices:
            futures = list()
            for device_id in changed_devices:
                logger.info("name of '{}' changed to '{}'".format(device_id, queried_devices[device_id][0]["name"]))
                device = self.__device_manager.get(device_id)
                prev_device_name = device.name
                device.name = queried_devices[device_id][0]["name"]
                futures.append((device, prev_device_name, self.__client.updateDevice(device, asynchronous=True)))
            for device, prev_device_name, future in futures:
                future.wait()
                try:
                    future.result()
                except cc_lib.client.DeviceUpdateError:
                    device.name = prev_device_name
        if any((missing_devices, new_devices, changed_devices)):
            try:
                self.__client.syncHub(list(self.__device_manager.devices.values()), asynchronous=True)
            except cc_lib.client.HubError:
                pass
