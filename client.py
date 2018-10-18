"""
   Copyright 2018 InfAI (CC SES)

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

try:
    from dyson.logger import root_logger
    from connector_client.modules.device_pool import DevicePool
    from connector_client.client import Client
    from dyson.session import SessionManager
    from dyson.discovery import startDiscovery
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json

logger = root_logger.getChild(__name__)


def router():
    while True:
        task = Client.receive()
        try:
            for part in task.payload.get('protocol_parts'):
                if part.get('name') == 'data':
                    command = json.loads(part.get('value'))
                session = SessionManager.sessions.get(task.payload.get('device_url'))
                session.command_queue.put(command)
                Client.response(task, '200')
        except Exception as ex:
            Client.response(task, '500')
            logger.error("could not route command '{}' for '{}'".format(task.payload.get('protocol_parts'), task.payload.get('device_url')))
            logger.error(ex)


if __name__ == '__main__':
    startDiscovery(15)
    connector_client = Client(device_manager=DevicePool)
    router()
