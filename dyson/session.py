try:
    from modules.logger import root_logger
    from modules.device_pool import DevicePool
    from connector.client import Client
    from dyson.device import DysonDevice
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time, json
from threading import Thread
from queue import Queue, Empty
import paho.mqtt.client as mqtt


logger = root_logger.getChild(__name__)


class Session(Thread):
    def __init__(self, device: DysonDevice, ip_address, port):
        super().__init__()
        self.device = device
        self.ip_address = ip_address
        self.port = port
        self.stop = False
        self.publish_queue = Queue()
        self.device_sensor_request = Thread(target=self.__requestDeviceSensorStates, name='{}-sensor-request'.format(self.device.id))
        self.mqtt_c = mqtt.Client()
        self.mqtt_c.on_message = self.__on_message
        self.mqtt_c.on_connect = self.__on_connect
        self.mqtt_c.on_disconnect = self.__on_disconnect
        self.mqtt_c.username_pw_set(device.id, device.credentials)
        self.start()

    def run(self):
        logger.info("starting session for '{}'".format(self.device.id))
        try:
            self.mqtt_c.connect(self.ip_address, self.port, keepalive=5)
            self.mqtt_c.loop_start()
            while not self.stop:
                try:
                    data = self.publish_queue.get(timeout=0.5)
                    payload = {
                        "msg": "STATE-SET",
                        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "mode-reason": "LAPP",
                        "data": data
                    }
                    self.mqtt_c.publish('{}/{}/command'.format(self.device.product_type, self.device.id), json.dumps(payload), 1)
                except Empty:
                    pass
            try:
                Client.disconnect(self.device)
            except AttributeError:
                DevicePool.remove(self.device)
        except Exception as ex:
            self.mqtt_c.loop_stop()
            logger.error("could not connect to broker '{}' on '{}' - reason '{}'".format(self.ip_address, self.port, ex))
        if self.device_sensor_request.is_alive():
            self.device_sensor_request.join()
        SessionManager.cleanSession(self.device.id)

    def shutdown(self):
        self.mqtt_c.disconnect()

    def __requestDeviceSensorStates(self):
        while not self.stop:
            time.sleep(10)
            payload = {
                "msg": "REQUEST-PRODUCT-ENVIRONMENT-CURRENT-SENSOR-DATA",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self.mqtt_c.publish('{}/{}/command'.format(self.device.product_type, self.device.id), json.dumps(payload))
        logger.debug("sensor request for '{}' stopped".format(self.device.id))

    def __on_message(self, client, userdata, message):
        try:
            message = json.loads(message.payload.decode())
            if message['msg'] == 'ENVIRONMENTAL-CURRENT-SENSOR-DATA':
                for reading in self.device.getEnvironmentSensors(message):
                    logger.info(reading)
            elif message['msg'] in ['CURRENT-STATE', 'STATE-CHANGE']:
                pass
            else:
                logger.warning("unknown message: '{}'".format(message))
        except Exception as ex:
            logger.error("malformed message: '{}'".format(ex))

    def __on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("connected to broker '{}' on '{}'".format(self.ip_address, self.port))
            self.mqtt_c.subscribe("{0}/{1}/status/current".format(self.device.product_type, self.device.id))
            try:
                Client.add(self.device)
            except AttributeError:
                DevicePool.add(self.device)
            self.device_sensor_request.start()
        else:
            logger.error("could not connect to broker '{}' on '{}' - reason '{}'".format(self.ip_address, self.port, rc))

    def __on_disconnect(self, client, userdata, rc):
        self.mqtt_c.loop_stop()
        self.stop = True
        if rc == 0:
            logger.info("connection to broker '{}' on '{}' closed by client".format(self.ip_address, self.port))
        else:
            logger.error("connection to broker '{}' on '{}' closed unexpectedly - reason '{}'".format(self.ip_address, self.port, rc))


class SessionManager:
    sessions = dict()
    local_devices = dict()
    remote_devices = dict()

    @staticmethod
    def addRemoteDevice(device: DysonDevice):
        __class__.remote_devices[device.id] = device
        if device.id in __class__.local_devices and device.id not in __class__.sessions:
            __class__.sessions[device.id] = Session(device, **__class__.local_devices[device.id])
            logger.debug('started session via addRemoteDevice')

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
            logger.debug('started session via addLocalDevice')

    @staticmethod
    def delLocalDevice(device_id):
        del __class__.local_devices[device_id]

    @staticmethod
    def cleanSession(device_id):
        logger.info("session for '{}' closed".format(device_id))
        time.sleep(5)
        if device_id in __class__.remote_devices and device_id in __class__.local_devices:
            logger.info("restarting session for '{}'".format(device_id))
            __class__.sessions[device_id] = Session(__class__.remote_devices[device_id], **__class__.local_devices[device_id])
        else:
            del __class__.sessions[device_id]
            logger.info("removed session for '{}'".format(device_id))