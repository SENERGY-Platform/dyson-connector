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

__all__ = ('commandRouter',)

from .configuration import config
from .logger import root_logger
import time, json, cc_lib


logger = root_logger.getChild(__name__.split(".", 1)[-1])


def commandRouter(connector_client: cc_lib.client.Client, device_manager):
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
