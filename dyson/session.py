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
from .util import LockingDict
from libpurecoollink.utils import decrypt_password
import paho.mqtt.client as mqtt
import time, json, threading, queue, typing, cc_lib


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

    def run(self):
        logger.info("starting session for '{}' ...".format(self.__device_id))
        while True:
            try:
                self.__mqtt_client.connect(self.__ip, self.__port, keepalive=config.Session.keepalive)
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
        logger.info("session for '{}' closed".format(self.__device_id))

            # self.init_state.wait(timeout=10)
            # if self.__device.state:
            #     while not self.stop:
            #         try:
            #             command = self.command_queue.get(timeout=0.5)
            #             state = self.__device.state
            #             for key, value in command.items():
            #                 if key in DysonDevice.state_map and value in DysonDevice.state_map[key]:
            #                     state[key] = value
            #             payload = {
            #                 "msg": "STATE-SET",
            #                 "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            #                 "mode-reason": "LAPP",
            #                 "data": state
            #             }
            #             self.__mqtt_client.publish('{}/{}/command'.format(self.__device.product_type, self.__device.id), json.dumps(payload), 1)
            #         except queue.Empty:
            #             pass
            #         except Exception as ex:
            #             logger.error("error handling command - '{}'".format(ex))
            #     try:
            #         Client.disconnect(self.__device)
            #     except AttributeError:
            #         DevicePool.remove(self.__device)
            # else:
            #     self.__mqtt_client.disconnect()
            #     logger.error("could not get device state for '{}'".format(self.__device.id))

    def __trigger_device_state(self):
        payload = {
            "msg": "REQUEST-CURRENT-STATE",
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.__mqtt_client.publish('{}/{}/command'.format(self.__model_num, self.__device_id), json.dumps(payload))

    def __trigger_sensor_data(self):
        logger.debug("starting sensor trigger for '{}' ...".format(self.__device_id))
        while True:
            if self.__mqtt_client.is_connected():
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
    #
    # def __on_message(self, client, userdata, message):
    #     try:
    #         message = json.loads(message.payload.decode())
    #         if message['msg'] == 'ENVIRONMENTAL-CURRENT-SENSOR-DATA':
    #             for reading in self.__device.parseEnvironmentSensors(message):
    #                 Client.event(
    #                     self.__device,
    #                     reading[0],
    #                     json.dumps({
    #                         'value': reading[1],
    #                         'unit': reading[2],
    #                         'time': reading[3]
    #                     }),
    #                     block=False
    #                 )
    #                 time.sleep(0.1)
    #         elif message['msg'] == 'CURRENT-STATE':
    #             self.__device.state = message.get('product-state')
    #             if not self.init_state.is_set():
    #                 self.init_state.set()
    #         elif message['msg'] == 'STATE-CHANGE':
    #             self.__device.updateState(message.get('product-state'))
    #         else:
    #             logger.warning("unknown message: '{}'".format(message))
    #     except Exception as ex:
    #         logger.error("malformed message: '{}'".format(ex))

    def __on_message(self, client, userdata, message: mqtt.MQTTMessage):
        logger.debug(message.payload)

    def __on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.__discon_count = 0
            logger.info("connected to '{}'".format(self.__device_id))
            self.__mqtt_client.subscribe("{}/{}/status/current".format(self.__model_num, self.__device_id))
            self.__trigger_device_state()
            try:
                self.__client.connectDevice(self.__device_id)
            except (cc_lib.client.DeviceConnectError, cc_lib.client.NotConnectedError):
                pass
        else:
            logger.error("could not connect to '{}' - {}".format(self.__device_id, mqtt.connack_string(rc)))
        # if rc == 0:
        #     logger.info("connected to broker '{}' on '{}'".format(self.__ip, self.__port))
        #     self.__mqtt_client.subscribe("{0}/{1}/status/current".format(self.__device.product_type, self.__device.id))
        #     try:
        #         Client.add(self.__device)
        #     except AttributeError:
        #         DevicePool.add(self.__device)
        #     self.__requestDeviceStates()
        #     self.device_sensor_request.start()
        # else:
        #     logger.error("could not connect to broker '{}' on '{}' - reason '{}'".format(self.__ip, self.__port, rc))

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
