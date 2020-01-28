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


from dyson.configuration import config
from dyson.device_manager import DeviceManager
from dyson.discovery.cloud_monitor import CloudMonitor
from dyson.discovery.local_monitor import LocalMonitor
from dyson.router import commandRouter
import time, random, cc_lib


if config.RuntimeEnv.max_start_delay > 0:
    delay = random.randint(1, config.RuntimeEnv.max_start_delay)
    print("delaying start for {}s".format(delay))
    time.sleep(delay)


device_manager = DeviceManager()


def on_connect(client: cc_lib.client.Client):
    devices = device_manager.devices
    for device in devices.values():
        if device.session:
            device.session.connect_device_to_platform()


connector_client = cc_lib.client.Client()
connector_client.setConnectClbk(on_connect)


cloud_monitor = CloudMonitor(device_manager, connector_client)
local_monitor = LocalMonitor(device_manager, connector_client)


if __name__ == '__main__':
    while True:
        try:
            connector_client.initHub()
            break
        except cc_lib.client.HubInitializationError:
            time.sleep(10)
    connector_client.connect(reconnect=True)
    cloud_monitor.start()
    local_monitor.start()
    try:
        commandRouter(connector_client, device_manager)
    except KeyboardInterrupt:
        print("\ninterrupted by user\n")
