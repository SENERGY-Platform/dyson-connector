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

__all__ = ('SetPower', 'SetOscillation', 'SetSpeed')


from ..logger import root_logger
import cc_lib


logger = root_logger.getChild(__name__.split(".", 1)[-1])


class SetPower(cc_lib.types.Service):
    local_id = "setPower"

    @staticmethod
    def task(device, power: bool):
        if power:
            err = device.session.setState({"fmod": "ON"})
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
