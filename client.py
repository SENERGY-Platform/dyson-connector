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


logger = root_logger.getChild(__name__)


"""
"fmod": fan mode,
"fnsp": speed,
"oson": oscillation,
"sltm": sleep_timer,
"rhtm": standby_monitoring,  # monitor air quality when inactive
"rstf": reset_filter,  # reset filter lifecycle
"qtar": quality_target,
"nmod": night_mode
"""


def router():
    import time
    session = SessionManager.sessions.get('NN2-EU-HKA3617A')
    time.sleep(5)
    session.command_queue.put({'fnst': 'FAN', 'fnsp': '0005'})
    time.sleep(10)
    session.command_queue.put({'oson': 'ON'})
    time.sleep(10)
    session.command_queue.put({'fnsp': '0003'})
    time.sleep(20)
    session.command_queue.put({'fnst': 'OFF'})
    time.sleep(10)
    session.shutdown()


if __name__ == '__main__':
    startDiscovery()
    #connector_client = Client(device_manager=DevicePool)
    router()
