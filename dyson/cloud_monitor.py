"""
   Copyright 2019 InfAI (CC SES)

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

from .configuration import config
from dyson.device import DysonDevice, dyson_map
from dyson.session import SessionManager
from libpurecoollink.utils import decrypt_password
from dyson.logger import root_logger
import time, requests, cc_lib
from threading import Thread


logger = root_logger.getChild(__name__.split(".", 1)[-1])


class CloudMonitor(Thread):
    def __init__(self, client: cc_lib.client.Client):
        super().__init__(name=__class__.__name__, daemon=True)
        self.__client = client
        self.__know_devices = list()

    def run(self):
        if not (config.Cloud.user and config.Cloud.pw):
            while not self._getApiCredentials():
                logger.info("retry in 30s")
                time.sleep(30)
        while True:
            unknown_devices = self._apiQueryDevices()
            self._evaluate(unknown_devices)
            time.sleep(config.Cloud.poll_interval)

    def _getApiCredentials(self):
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
        logger.error("could not retrieve dyson cloud credentials - '{}' - '{}'".format(http_resp.status_code, http_resp.raw))
        return False

    def _apiQueryDevices(self):
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
                    unknown_devices[device['Serial']] = device
                except KeyError:
                    logger.error("missing device serial or malformed message - '{}'".format(device))
        return unknown_devices

    def _diff(self, known, unknown):
        known_set = set(known)
        unknown_set = set(unknown)
        missing = known_set - unknown_set
        new = unknown_set - known_set
        return missing, new

    def _evaluate(self, unknown_devices):
        missing_devices, new_devices = self._diff(self.__know_devices, unknown_devices)
        if missing_devices:
            for missing_device_id in missing_devices:
                logger.info("can't find '{}'".format(missing_device_id))
                try:
                    Client.disconnect(missing_device_id)
                except AttributeError:
                    DevicePool.remove(missing_device_id)
                SessionManager.delRemoteDevice(missing_device_id)
        if new_devices:
            for new_device_id in new_devices:
                try:
                    dyson_data = dyson_map[unknown_devices[new_device_id]['ProductType']]
                    dyson_device = DysonDevice(
                        new_device_id,
                        dyson_data['type'],
                        dyson_data['name'],
                        decrypt_password(unknown_devices[new_device_id]['LocalCredentials']),
                        unknown_devices[new_device_id]['ProductType'],
                        unknown_devices[new_device_id]['ScaleUnit']
                    )
                    dyson_device.addTag('manufacturer', 'Dyson')
                    count = ''
                    for tag in dyson_data['tags']:
                        dyson_device.addTag('type{}'.format(count), tag)
                        if not count:
                            count = 0
                        count = count + 1
                    logger.info("found '{}' with id '{}'".format(dyson_device.name, dyson_device.id))
                    SessionManager.addRemoteDevice(dyson_device)
                except KeyError:
                    logger.error("missing device data or malformed message - '{}'".format(unknown_devices[new_device_id]))
        self.__know_devices = unknown_devices.keys()
