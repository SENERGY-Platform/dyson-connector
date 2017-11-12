import os, sys, inspect
import_path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0],"connector_client")))
if import_path not in sys.path:
    sys.path.insert(0, import_path)


try:
    from modules.logger import root_logger
    from modules.device_pool import DevicePool
    from connector.client import Client
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
                    logger.info(command)
                session = SessionManager.sessions.get(task.payload.get('device_url'))
                session.command_queue.put(command)
        except Exception as ex:
            logger.error("could not route command '{}' for '{}'".format(task.payload.get('protocol_parts'), task.payload.get('device_url')))
            logger.error(ex)

def test():
    import time
    logger.info("start test")
    session = SessionManager.sessions.get('NN2-EU-HKA3617A')
    session.command_queue.put({'fmod': 'FAN', 'fnsp': '0005'})
    time.sleep(10)
    session.command_queue.put({'oson': 'ON'})
    time.sleep(10)
    session.command_queue.put({'fnsp': '0003'})
    time.sleep(10)
    session.command_queue.put({'fnsp': '0010'})
    time.sleep(5)
    session.command_queue.put({'fmod': 'OFF'})


if __name__ == '__main__':
    startDiscovery(15)
    connector_client = Client(device_manager=DevicePool)
    router()
