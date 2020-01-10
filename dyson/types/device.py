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

__all__ = ('device_type_map', 'DysonPureCoolLink')


from ..configuration import config
from .service import SetPower, SetOscillation, SetSpeed, SetMonitoring, GetSensorReadings, GetDeviceState
import cc_lib


class DysonPureCoolLink(cc_lib.types.Device):
    device_type_id = config.Senergy.dt_pure_cool_link
    services = (SetPower, SetOscillation, SetSpeed, SetMonitoring, GetSensorReadings, GetDeviceState)
    model_num = "475"

    def __init__(self, id: str, pw: str, name: str):
        self.id = id
        self.pw = pw
        self.name = name
        self.session = None

    def __iter__(self):
        items = (
            ("name", self.name),
        )
        for item in items:
            yield item


class DysonPureCoolLinkDesk(cc_lib.types.Device):
    # device_type_id =
    # services =
    model_num = "469"


class DysonPureHotCoolLink(cc_lib.types.Device):
    # device_type_id =
    # services =
    model_num = "455"


device_type_map = {dt.model_num: dt for dt in (DysonPureCoolLink, DysonPureCoolLinkDesk, DysonPureHotCoolLink)}
