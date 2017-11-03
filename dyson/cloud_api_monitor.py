try:
    from modules.logger import root_logger
    from modules.device_pool import DevicePool
    from connector.client import Client
    from libpurecoollink.dyson import DysonAccount
    from libpurecoollink.exceptions import DysonNotLoggedException
    from dyson.device_session import DeviceSession
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time
from threading import Thread


logger = root_logger.getChild(__name__)


dyson_account_user = 'smart.energy.platform@gmail.com'
dyson_account_pass = 'connector1!'


class CloudApiMonitor(Thread):
    def __init__(self):
        super().__init__()
        self._dyson_account = DysonAccount(dyson_account_user, dyson_account_pass, "DE")
        self._apiLogin()
        self._init_sessions = list()
        unknown_devices = self._apiQueryDevices()
        if unknown_devices:
            self._evaluate(unknown_devices, True)
        self.start()


    def run(self):
        for session in self._init_sessions:
            session.start()
        while True:
            time.sleep(300)
            self._apiLogin()
            unknown_devices = self._apiQueryDevices()
            if unknown_devices:
                self._evaluate(unknown_devices, False)


    def _apiLogin(self):
        while True:
            if self._dyson_account.login():
                logger.info("login to Dyson account with '{}' successful".format(dyson_account_user))
                break
            else:
                logger.error('unable to login to Dyson account')
                logger.info('retrying in 30s')
                time.sleep(30)


    def _apiQueryDevices(self):
        unknown_devices = dict()
        try:
            devices = self._dyson_account.devices()
            for device in devices:
                unknown_devices[device.serial] = device
            return unknown_devices
        except DysonNotLoggedException:
            pass


    def _diff(self, known, unknown):
        known_set = set(known)
        unknown_set = set(unknown)
        missing = known_set - unknown_set
        new = unknown_set - known_set
        return missing, new


    def _evaluate(self, unknown_devices, init):
        missing_devices, new_devices = self._diff(DevicePool.devices(), unknown_devices)
        if missing_devices:
            for missing_device_id in missing_devices:
                logger.info("can't find '{}'".format(missing_device_id))
                if init:
                    DevicePool.remove(missing_device_id)
                else:
                    Client.delete(missing_device_id)
        if new_devices:
            for new_device_id in new_devices:
                logger.info("found Dyson device with id '{}'".format(new_device_id))
                if init:
                    self._init_sessions.append(DeviceSession(unknown_devices[new_device_id], init))
                else:
                    device_session = DeviceSession(unknown_devices[new_device_id], init)
                    device_session.start()
