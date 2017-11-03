try:
    from modules.logger import root_logger
    from modules.device_pool import DevicePool
    from connector.client import Client
    from connector.device import Device
    from libpurecoollink.dyson_360_eye import Dyson360Eye
    from libpurecoollink.dyson_pure_cool_link import DysonPureCoolLink
    from libpurecoollink.dyson_pure_hotcool_link import DysonPureHotCoolLink
    from libpurecoollink.dyson_pure_state import DysonPureHotCoolState, DysonPureCoolState, DysonEnvironmentalSensorState
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time
from threading import Thread


logger = root_logger.getChild(__name__)


dyson_map = {
    Dyson360Eye: {
        'name': 'Dyson 360 Eye',
        'types': ('Vacuum', )
    },
    DysonPureCoolLink: {
        'name': 'Dyson Pure Cool Link',
        'types': ('Fan', 'Purifier')
    },
    DysonPureHotCoolLink: {
        'name': 'Dyson Pure Hot + Cool Link',
        'types': ('Fan', 'Heater', 'Purifier')
    }
}


class DeviceWrapper(Device):
    def __init__(self, id, type, name, dyson_obj):
        super().__init__(id, type, name)
        self.dyson = dyson_obj


class DeviceSession(Thread):
    def __init__(self, dyson_device: DysonPureCoolLink, init):
        super().__init__()
        self._shutdown = False
        self._init = init
        self.dyson_obj = dyson_device
        dyson_type = dyson_map[type(self.dyson_obj)]
        self.device = DeviceWrapper(self.dyson_obj.serial, 'iot#784c1e30-e291-4840-a9a5-2658936e4813', dyson_type['name'], self.dyson_obj)
        self.device.addTag('room', self.dyson_obj.name)
        self.device.addTag('manufacturer', 'Dyson')
        count = ''
        for d_type in dyson_type['types']:
            self.device.addTag('type{}'.format(count), d_type)
            if not count:
                count = 0
            count = count + 1
        if self._init:
            if self._connectToDevice():
                self._registerDevice(True)
                self._init = False
        logger.info(self.dyson_obj.network_device)

    def run(self):
        while not self._shutdown:
            if not self.dyson_obj.connected:
                if not self._init:
                    Client.disconnect(self.device)
                    self._init = True
                if self._connectToDevice():
                    self._registerDevice(False)
                    self._init = False
            time.sleep(1)


    def _connectToDevice(self):
        logger.info("trying to connect to '{}'".format(self.dyson_obj.serial))
        try:
            net_conf = self.dyson_obj.find_device()
            if net_conf:
                logger.info("found '{}' at '{}'".format(self.dyson_obj.serial, net_conf.address))
                if self.dyson_obj.connect(net_conf.address, net_conf.port):
                    self._waitForDevice()
                    logger.info("connected to '{}'".format(self.dyson_obj.serial))
                    return True
            else:
                logger.error("could not find '{}' in local network".format(self.dyson_obj.serial))
        except Exception:
            pass


    def _waitForDevice(self):
        while not self.dyson_obj.device_available:
            if self._shutdown:
                break
            logger.info("waiting for '{}' to be available".format(self.dyson_obj.serial))
            time.sleep(0.5)


    def _registerDevice(self, init):
        if init:
            DevicePool.add(self.device)
        else:
            Client.add(self.device)


    def stop(self):
        self._shutdown = True
        if self.dyson_obj.connected:
            self.dyson_obj.disconnect()
        self.join()


    #def _reconnectToDevice(self):
    #    reconnect_thread = Thread(target=self._connectToDevice, name='{}-reconnect'.format(self.dyson_obj.serial))