try:
    from modules.logger import root_logger
    from connector.client import Client
    from modules.device_pool import DevicePool
    from modules.http_lib import Methods as http
    from dyson.configuration import DYSON_CLOUD_API_URL, DYSON_ACCOUNT_EMAIL, DYSON_ACCOUNT_PW, DYSON_ACCOUNT_COUNTRY, DYSON_CLOUD_API_USER, DYSON_CLOUD_API_PW, writeConf
    from dyson.device import DysonDevice, dyson_map
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time, json
from threading import Thread
import base64
from Crypto.Cipher import AES


logger = root_logger.getChild(__name__)


def unpad(string):
    """Un pad string."""
    return string[:-ord(string[len(string) - 1:])]

def decryptPassword(encrypted_password):
    """Decrypt password.

    :param encrypted_password: Encrypted password
    """
    key = b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10' \
          b'\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f '
    init_vector = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                  b'\x00\x00\x00\x00'
    cipher = AES.new(key, AES.MODE_CBC, init_vector)
    json_password = json.loads(unpad(cipher.decrypt(base64.b64decode(encrypted_password)).decode('utf-8')))
    return json_password["apPasswordHash"]


class CloudApiMonitor(Thread):
    def __init__(self):
        super().__init__()
        self._init_sessions = list()
        if not (DYSON_CLOUD_API_USER and DYSON_CLOUD_API_PW):
            while not self._getApiCredentials():
                logger.info("retry in 30s")
                time.sleep(30)
        unknown_devices = self._apiQueryDevices()
        if unknown_devices:
            self._evaluate(unknown_devices, True)
        self.start()


    def run(self):
        for session in self._init_sessions:
            session.start()
        while True:
            time.sleep(300)
            unknown_devices = self._apiQueryDevices()
            if unknown_devices:
                self._evaluate(unknown_devices, False)


    def _getApiCredentials(self):
        body = {
            "Email": DYSON_ACCOUNT_EMAIL,
            "Password": DYSON_ACCOUNT_PW
        }
        http_resp = http.post(
            "https://{}/v1/userregistration/authenticate?country={}".format(DYSON_CLOUD_API_URL, DYSON_ACCOUNT_COUNTRY),
            json.dumps(body),
            headers={'Content-Type': 'application/json'}
        )
        if http_resp.status == 200:
            credentials = json.loads(http_resp.body)
            global DYSON_CLOUD_API_USER
            global DYSON_CLOUD_API_PW
            DYSON_CLOUD_API_USER = credentials.get('Account')
            DYSON_CLOUD_API_PW = credentials.get('Password')
            writeConf('CLOUD_API', 'user', DYSON_CLOUD_API_USER)
            writeConf('CLOUD_API', 'pw', DYSON_CLOUD_API_PW)
            return True
        logger.error("could not retrieve dyson cloud credentials - '{}' - '{}'".format(http_resp.status, http_resp.body))
        return False


    def _apiQueryDevices(self):
        unknown_devices = dict()
        http_resp = http.get(
            "https://api.cp.dyson.com/v1/provisioningservice/manifest",
            auth=(DYSON_CLOUD_API_USER, DYSON_CLOUD_API_PW)
        )
        if http_resp.status == 200:
            devices = json.loads(http_resp.body)
            for device in devices:
                try:
                    unknown_devices[device['Serial']] = device
                except KeyError:
                    logger.error("missing device serial or malformed message - '{}'".format(device))
        return unknown_devices


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
                try:
                    dyson_data = dyson_map[unknown_devices[new_device_id]['ProductType']]
                    device_credentials = decryptPassword(unknown_devices[new_device_id]['LocalCredentials'])
                    dyson_device = DysonDevice(
                        new_device_id,
                        dyson_data['type'],
                        dyson_data['name'],
                        device_credentials,
                        unknown_devices[new_device_id]['ScaleUnit']
                    )
                    dyson_device.addTag('manufacturer', 'Dyson')
                    count = ''
                    for tag in dyson_data['tags']:
                        dyson_device.addTag('type{}'.format(count), tag)
                        if not count:
                            count = 0
                        count = count + 1
                    logger.info("found '{}' with id '{}'".format(dyson_device.name, dyson_device.id))
                    logger.info(dyson_device)
                except KeyError:
                    logger.error("missing device data or malformed message - '{}'".format(unknown_devices[new_device_id]))