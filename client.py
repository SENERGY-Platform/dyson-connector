import os, sys, inspect
import_path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0],"connector_client")))
if import_path not in sys.path:
    sys.path.insert(0, import_path)


try:
    from modules.logger import root_logger
    from modules.device_pool import DevicePool
    from connector.client import Client
    from dyson.cloud_api_monitor import CloudApiMonitor
    from libpurecoollink.const import FanSpeed, FanMode, NightMode, Oscillation, FanState, StandbyMonitoring, QualityTarget, ResetFilter, HeatMode, FocusMode, HeatTarget
    from libpurecoollink.dyson_device import DysonDevice
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time

logger = root_logger.getChild(__name__)


def dysonController():
    device = DevicePool.get('NN2-EU-HKA3617A')
    device.dyson.set_configuration(fan_mode=FanMode.FAN, fan_speed=FanSpeed.FAN_SPEED_3, oscillation=Oscillation.OSCILLATION_OFF)
    time.sleep(10)
    device.dyson.set_configuration(fan_mode=FanMode.OFF)
    logger.info(device.dyson.status_topic)


if __name__ == '__main__':
    dyson_monitor = CloudApiMonitor()
    #connector_client = Client(device_manager=DevicePool)
    dysonController()
