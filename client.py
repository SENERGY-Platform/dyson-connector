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
