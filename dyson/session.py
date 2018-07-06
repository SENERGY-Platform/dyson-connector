try:
    from dyson.logger import root_logger
    from connector_client.modules.device_pool import DevicePool
    from connector_client.client import Client
    from dyson.device import DysonDevice
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import time, json
from threading import Thread, Event
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
        self.command_queue = Queue()
        self.init_state = Event()
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
            self.init_state.wait(timeout=10)
            if self.device.state:
                while not self.stop:
                    try:
                        command = self.command_queue.get(timeout=0.5)
                        state = self.device.state
                        for key, value in command.items():
                            if key in DysonDevice.state_map and value in DysonDevice.state_map[key]:
                                state[key] = value
                        payload = {
                            "msg": "STATE-SET",
                            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "mode-reason": "LAPP",
                            "data": state
                        }
                        self.mqtt_c.publish('{}/{}/command'.format(self.device.product_type, self.device.id), json.dumps(payload), 1)
                    except Empty:
                        pass
                    except Exception as ex:
                        logger.error("error handling command - '{}'".format(ex))
                try:
                    Client.disconnect(self.device)
                except AttributeError:
                    DevicePool.remove(self.device)
            else:
                self.mqtt_c.disconnect()
                logger.error("could not get device state for '{}'".format(self.device.id))
        except TimeoutError as ex:
            logger.error("could not connect to broker '{}' on '{}' - reason '{}'".format(self.ip_address, self.port, ex))
        self.mqtt_c.loop_stop()
        if self.device_sensor_request.is_alive():
            self.device_sensor_request.join()
        SessionManager.cleanSession(self.device.id)

    def shutdown(self):
        self.mqtt_c.disconnect()

    def __requestDeviceStates(self):
        payload = {
            "msg": "REQUEST-CURRENT-STATE",
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.mqtt_c.publish('{}/{}/command'.format(self.device.product_type, self.device.id), json.dumps(payload))

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
                for reading in self.device.parseEnvironmentSensors(message):
                    Client.event(
                        self.device,
                        reading[0],
                        json.dumps({
                            'value': reading[1],
                            'unit': reading[2],
                            'time': reading[3]
                        }),
                        block=False
                    )
                    time.sleep(0.1)
            elif message['msg'] == 'CURRENT-STATE':
                self.device.state = message.get('product-state')
                if not self.init_state.is_set():
                    self.init_state.set()
            elif message['msg'] == 'STATE-CHANGE':
                self.device.updateState(message.get('product-state'))
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
            self.__requestDeviceStates()
            self.device_sensor_request.start()
        else:
            logger.error("could not connect to broker '{}' on '{}' - reason '{}'".format(self.ip_address, self.port, rc))

    def __on_disconnect(self, client, userdata, rc):
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