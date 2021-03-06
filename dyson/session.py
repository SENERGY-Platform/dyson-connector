"""
   Copyright 2020 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""


from .configuration import config
from .logger import root_logger
from .util import LockingDict, decrypt_password
import paho.mqtt.client as mqtt
import time, json, threading, cc_lib


logger = root_logger.getChild(__name__.split(".", 1)[-1])


class Session(threading.Thread):
    def __init__(self, client: cc_lib.client.Client, model_num: str, device_id: str, pw: str, ip:str , port: int):
        super().__init__(name="Session-{}".format(device_id), daemon=True)
        self.__client = client
        self.__model_num = model_num
        self.__device_id = device_id
        self.__ip = ip
        self.__port = port
        self.__mqtt_client = mqtt.Client()
        self.__mqtt_client.on_connect = self.__on_connect
        self.__mqtt_client.on_disconnect = self.__on_disconnect
        self.__mqtt_client.on_message = self.__on_message
        self.__mqtt_client.username_pw_set(self.__device_id, decrypt_password(pw))
        if config.Session.logging:
            self.__mqtt_client.enable_logger(logger.getChild(self.__device_id))
        self.__discon_count = 0
        self.__stop = False
        self.__sensor_trigger = threading.Thread(target=self.__trigger_sensor_data, name="-Sensor-Trigger".format(self.name), daemon=True)
        self.__device_state = LockingDict()
        self.__push_sensor_data_service = None

    def setSensorDataService(self, service):
        self.__push_sensor_data_service = service

    def stop(self):
        if not self.__stop:
            self.__stop = True
            self.__mqtt_client.disconnect()
            self.join()

    def __cleanState(self, state):
        odd_keys = ['filf', 'fnst', 'ercd', 'wacd']
        missing_keys = {'sltm': 'STET', 'rstf': 'STET'}
        for key in odd_keys:
            try:
                del state[key]
            except KeyError:
                pass
        for key, value in missing_keys.items():
            state[key] = value

    def getState(self):
        return self.__device_state.copy()

    def setState(self, state):
        if not self.__mqtt_client.is_connected():
            return "not connected to '{}'".format(self.__device_id)
        if not self.__device_state:
            return "device '{}' not ready".format(self.__device_id)
        try:
            device_state = self.__device_state.copy()
            device_state.update(state)
            self.__cleanState(device_state)
            payload = {
                "msg": "STATE-SET",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "mode-reason": "LAPP",
                "data": device_state
            }
            self.__mqtt_client.publish('{}/{}/command'.format(self.__model_num, self.__device_id), json.dumps(payload), 1)
        except Exception as ex:
            return "error setting state for '{}' - {}".format(self.__device_id, ex)
        return False

    def connect_device_to_platform(self):
        if self.__mqtt_client.is_connected():
            try:
                self.__client.connectDevice(self.__device_id)
            except (cc_lib.client.DeviceConnectError, cc_lib.client.NotConnectedError):
                pass

    def run(self):
        logger.info("starting session for '{}' ...".format(self.__device_id))
        while True:
            try:
                self.__mqtt_client.connect(self.__ip, self.__port, keepalive=config.Session.keepalive)
                if not self.__sensor_trigger.is_alive():
                    self.__sensor_trigger.start()
            except Exception as ex:
                logger.error("could not connect to '{}' at '{}' on '{}' - {}".format(self.__device_id, self.__ip, self.__port, ex))
            try:
                self.__mqtt_client.loop_forever()
            except Exception as ex:
                logger.error("mqtt loop broke - {}".format(ex))
            if self.__stop:
                break
            else:
                time.sleep(2)
        self.__sensor_trigger.join()
        logger.info("session for '{}' closed".format(self.__device_id))

    def __trigger_device_state(self):
        payload = {
            "msg": "REQUEST-CURRENT-STATE",
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.__mqtt_client.publish('{}/{}/command'.format(self.__model_num, self.__device_id), json.dumps(payload), 1)

    def __trigger_sensor_data(self):
        logger.debug("starting sensor trigger for '{}' ...".format(self.__device_id))
        while True:
            if self.__mqtt_client.is_connected() and self.__device_state.get("rhtm") == "ON":
                logger.debug("triggering sensor data for '{}'".format(self.__device_id))
                payload = {
                    "msg": "REQUEST-PRODUCT-ENVIRONMENT-CURRENT-SENSOR-DATA",
                    "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                self.__mqtt_client.publish('{}/{}/command'.format(self.__model_num, self.__device_id), json.dumps(payload))
            if not self.__stop:
                time.sleep(config.Session.sensor_interval)
            else:
                break
        logger.debug("sensor trigger for '{}' stopped".format(self.__device_id))

    def __pushSensorData(self, data, timestamp):
        try:
            del data["sltm"]
        except KeyError:
            pass
        if all(val not in ("OFF", "INIT") for val in data.values()):
            envelope = cc_lib.client.message.EventEnvelope(
                device=self.__device_id,
                service=self.__push_sensor_data_service.local_id,
                message=cc_lib.client.message.Message(json.dumps(self.__push_sensor_data_service.task(data, timestamp)))
            )
            self.__client.emmitEvent(envelope, asynchronous=True)
        else:
            logger.debug("sensors of '{}' not ready".format(self.__device_id))

    def __on_message(self, client, userdata, message: mqtt.MQTTMessage):
        try:
            payload = json.loads(message.payload)
            if payload["msg"] == "CURRENT-STATE":
                if not self.__device_state:
                    self.__device_state.update(payload["product-state"])
                    logger.debug("got initial state for '{}'".format(self.__device_id))
            elif payload["msg"] == "STATE-CHANGE":
                self.__device_state.update({key :value[1] for key, value in payload["product-state"].items()})
                logger.debug("got new state for '{}'".format(self.__device_id))
            elif payload["msg"] == "ENVIRONMENTAL-CURRENT-SENSOR-DATA":
                if self.__device_state.get("rhtm") == "ON":
                    self.__pushSensorData(payload["data"], payload["time"])
            else:
                logger.warning("received unknown message type from '{}' - '{}'".format(self.__device_id, payload["msg"]))
        except Exception as ex:
            logger.error("failed parse message from '{}' - {}".format(self.__device_id, ex))

    def __on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.__discon_count = 0
            logger.info("connected to '{}'".format(self.__device_id))
            self.__mqtt_client.subscribe("{}/{}/status/current".format(self.__model_num, self.__device_id))
            self.__trigger_device_state()
            self.connect_device_to_platform()
        else:
            logger.error("could not connect to '{}' - {}".format(self.__device_id, mqtt.connack_string(rc)))

    def __on_disconnect(self, client, userdata, rc):
        if self.__discon_count < 1:
            if rc == 0:
                logger.info("disconnected from '{}'".format(self.__device_id))
            else:
                logger.warning("disconnected from '{}' unexpectedly".format(self.__device_id))
            try:
                self.__client.disconnectDevice(self.__device_id)
            except (cc_lib.client.DeviceDisconnectError, cc_lib.client.NotConnectedError):
                pass
            self.__discon_count+=1
