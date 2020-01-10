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

__all__ = ('SetPower', 'SetOscillation', 'SetSpeed', 'SetMonitoring', 'GetSensorReadings', 'GetDeviceState')


from ..logger import root_logger
import datetime, cc_lib


logger = root_logger.getChild(__name__.split(".", 1)[-1])


class SetPower(cc_lib.types.Service):
    local_id = "setPower"

    @staticmethod
    def task(device, power: bool):
        if power:
            err = device.session.setState({"fmod": "FAN"})
        else:
            err = device.session.setState({"fmod": "OFF"})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, err))
        return {"status": 1 if err else 0}


class SetOscillation(cc_lib.types.Service):
    local_id = "setOscillation"

    @staticmethod
    def task(device, oscillation: bool):
        if oscillation:
            err = device.session.setState({"oson": "ON"})
        else:
            err = device.session.setState({"oson": "OFF"})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, err))
        return {"status": 1 if err else 0}


class SetSpeed(cc_lib.types.Service):
    local_id = "setSpeed"

    @staticmethod
    def task(device, speed: int):
        err = device.session.setState({"fnsp": "{:04d}".format(speed)})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, err))
        return {"status": 1 if err else 0}


class SetMonitoring(cc_lib.types.Service):
    local_id = "setMonitoring"

    @staticmethod
    def task(device, monitoring: bool):
        if monitoring:
            err = device.session.setState({"rhtm": "ON"})
        else:
            err = device.session.setState({"rhtm": "OFF"})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, err))
        return {"status": 1 if err else 0}


class GetSensorReadings(cc_lib.types.Service):
    local_id = "getSensorReadings"

    @staticmethod
    def task(readings, timestamp):
        for key, value in readings.items():
            readings[key] = int(value)
        readings["time"] = timestamp
        return readings


class GetDeviceState(cc_lib.types.Service):
    local_id = "getDeviceState"
    value_map = {
        "FAN": True,
        "AUTO": True,
        "ON": True,
        "OFF": False,
    }

    @staticmethod
    def task(device):
        payload = {
            "status": 0,
            "power": False,
            "oscillation": False,
            "speed": 1,
            "monitoring": False,
            "filter_life": 0,
            "time": "{}Z".format(datetime.datetime.utcnow().isoformat())
        }
        state = device.session.getState()
        if not state:
            logger.error("'{}' for '{}' failed - device state not available".format(__class__.__name__, device.id))
            payload["status"] = 1
        else:
            try:
                payload["power"] = GetDeviceState.value_map[state["fmod"]]
                payload["oscillation"] = GetDeviceState.value_map[state["oson"]]
                payload["speed"] = 0 if state["fnsp"] == "AUTO" else int(state["fnsp"])
                payload["monitoring"] = GetDeviceState.value_map[state["rhtm"]]
                payload["filter_life"] = int(state["filf"])
            except KeyError as ex:
                logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, ex))
                payload["status"] = 1
        return payload
