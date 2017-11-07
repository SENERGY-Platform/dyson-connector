try:
    from modules.logger import root_logger
    from modules.device_pool import DevicePool
    from connector.client import Client
    from dyson.device import DysonDevice
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time
from threading import Thread, Event
import paho.mqtt.client as mqtt


logger = root_logger.getChild(__name__)


class Session(Thread):
    def __init__(self, device: DysonDevice, ip_address, port):
        super().__init__()
        self.device = device
        self.ip_address = ip_address
        self.port = port
        self.stop = False
        self.connected = False
        self.mqtt_c = mqtt.Client()
        self.mqtt_c.on_message = self.__on_message
        self.mqtt_c.on_connect = self.__on_connect
        self.mqtt_c.on_disconnect = self.__on_disconnect
        self.mqtt_c.username_pw_set(device.id, device.credentials)
        self.start()

    def run(self):
        self.mqtt_c.connect(self.ip_address, self.port, keepalive=10)
        while not self.stop:
            self.mqtt_c.loop()
        try:
            Client.disconnect(self.device)
        except AttributeError:
            DevicePool.remove(self.device)
        SessionManager.delSession(self.device.id)

    def shutdown(self):
        self.mqtt_c.disconnect()

    def __on_message(self):
        pass

    def __on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("connected to broker '{}' on '{}'".format(self.ip_address, self.port))
            try:
                Client.add(self.device)
            except AttributeError:
                DevicePool.add(self.device)
        else:
            logger.error("could not connect to broker '{}' on '{}' - reason '{}'".format(self.ip_address, self.port, rc))

    def __on_disconnect(self, client, userdata, rc):
        if rc == 0:
            logger.info("MQTT connection for '{}' on '{}' closed by client".format(self.ip_address, self.port))
        else:
            logger.error("MQTT connection for '{}' on '{}' closed unexpectedly - reason '{}'".format(self.ip_address, self.port, rc))
        self.stop = True


class SessionManager:
    sessions = dict()
    local_devices = dict()
    remote_devices = dict()

    @staticmethod
    def addRemoteDevice(device: DysonDevice):
        __class__.remote_devices[device.id] = device
        if device.id in __class__.local_devices and device.id not in __class__.sessions:
            __class__.sessions[device.id] = Session(device, *__class__.local_devices[device.id])
            logger.info('started session via addRemoteDevice')

    @staticmethod
    def delRemoteDevice(device_id):
        del __class__.remote_devices[device_id]
        session = __class__.sessions.get(device_id)
        if session:
            session.shutdown()

    @staticmethod
    def addLocalDevice(device_id, ip, port):
        __class__.local_devices[device_id] = {'ip_address': ip, 'port': port}
        if device_id in __class__.remote_devices and device_id not in __class__.sessions:
            __class__.sessions[device_id] = Session(__class__.remote_devices[device_id], ip, port)
            logger.info('started session via addLocalDevice')

    @staticmethod
    def delLocalDevice(device_id):
        del __class__.local_devices[device_id]

    @staticmethod
    def delSession(device_id):
        del __class__.sessions[device_id]