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
from dyson.logger import root_logger
from dyson.device_manager import DeviceManager
from dyson.discovery.cloud_monitor import CloudMonitor
from dyson.discovery.local_monitor import LocalMonitor
import time, json, cc_lib


logger = root_logger.getChild(__name__)


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


def router():
    while True:
        command = connector_client.receiveCommand()
        try:
            device = device_manager.get(command.device_id)
            logger.debug(command)
            if time.time() - command.timestamp <= config.Session.max_command_age:
                try:
                    if command.message.data:
                        data = device.getService(command.service_uri).task(device, **json.loads(command.message.data))
                    else:
                        data = device.getService(command.service_uri).task(device)
                    cmd_resp = cc_lib.client.message.Message(json.dumps(data))
                except json.JSONDecodeError as ex:
                    logger.error("could not parse command data for '{}' - {}".format(device.id, ex))
                    cmd_resp = cc_lib.client.message.Message(json.dumps({"status": 1}))
                except TypeError as ex:
                    logger.error("could not parse command response data for '{}' - {}".format(device.id, ex))
                    cmd_resp = cc_lib.client.message.Message(json.dumps({"status": 1}))
                command.message = cmd_resp
                if command.completion_strategy == cc_lib.client.CompletionStrategy.pessimistic:
                    logger.debug(command)
                    connector_client.sendResponse(command, asynchronous=True)
            else:
                logger.warning(
                    "dropped command for '{}' - max age exceeded - correlation id: {}".format(
                        device.id,
                        command.correlation_id
                    )
                )
        except KeyError:
            logger.error("received command for unknown device '{}'".format(command.device_id))


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
        router()
    except KeyboardInterrupt:
        print("\ninterrupted by user\n")
