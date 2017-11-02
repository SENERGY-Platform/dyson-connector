try:
    from modules.logger import root_logger
    from modules.device_pool import DevicePool
    from connector.client import Client
    from connector.device import Device
    from libpurecoollink.dyson_360_eye import Dyson360Eye
    from libpurecoollink.dyson_pure_cool_link import DysonPureCoolLink
    from libpurecoollink.dyson_pure_hotcool_link import DysonPureHotCoolLink
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
    def __init__(self, dyson_device: DysonPureCoolLink):
        super().__init__()
        self._shutdown = False
        self.dyson_obj = dyson_device
        dyson_type = dyson_map[type(self.dyson_obj)]
        self.device = DeviceWrapper(self.dyson_obj.serial, '##############', dyson_type['name'], self.dyson_obj)
        self.device.addTag('room', self.dyson_obj.name)
        self.device.addTag('manufacturer', 'Dyson')
        count = ''
        for d_type in dyson_type['types']:
            self.device.addTag('type{}'.format(count), d_type)
            if not count:
                count = 0
            count = count + 1
        if self._connectToDevice():
            self._registerDevice(True)


    def _connectToDevice(self):
        while not self.dyson_obj.connected:
            if self._shutdown:
                break
            else:
                logger.info("trying to connect to '{}'".format(self.dyson_obj.serial))
                try:
                    if self.dyson_obj.auto_connect(retry=1):
                        self._waitForDevice()
                        return True
                except Exception:
                    pass
                time.sleep(2)


    def _waitForDevice(self):
        while not self.dyson_obj.device_available:
            time.sleep(0.2)


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
