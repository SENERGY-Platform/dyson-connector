"""
   Copyright 2019 InfAI (CC SES)

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

from dyson.logger import root_logger
from dyson.configuration import SEPL_DEVICE_TYPE, SEPL_SERVICE_DUS, SEPL_SERVICE_HUM, SEPL_SERVICE_TEM, SEPL_SERVICE_VOL
from connector_lib.device import Device


logger = root_logger.getChild(__name__)


dyson_map = {
    '455': {
        'name': 'Dyson Pure Hot + Cool Link',
        'type': '',
        'tags': ('Fan', 'Heater', 'Purifier')
    },
    '469': {
        'name': 'Dyson Pure Cool Link Desk',
        'type': '',
        'tags': ('Fan', 'Purifier')
    },
    '475': {
        'name': 'Dyson Pure Cool Link',
        'type': SEPL_DEVICE_TYPE,
        'tags': ('Fan', 'Purifier')
    }
}


class DysonDevice(Device):
    state_map = {
        'fmod': ('OFF', 'FAN', 'AUTO'), # fan mode
        'fnsp': ('0001', '0002', '0003', '0004', '0005', '0006', '0007', '0008', '0009', '0010', 'AUTO'), # fan speed
        'oson': ('ON', 'OFF'), # oscillation
        'sltm': tuple(['STET'] + list(range(1, 1441))), # sleep timer
        'rhtm': ('ON', 'OFF'), # standby monitoring (monitor air quality when inactive)
        'rstf': ('RSTF', 'STET'), # reset filter
        'qtar': ('0001', '0003', '0004'), # quality target
        'nmod': ('ON', 'OFF'), # night mode
        'hmod': ('HEAT', 'OFF'), # heat mode
        'ffoc': ('ON', 'OFF'), # fan focus
        'hmax': tuple(range(2740, 3101)) # heat target from 1°C to 37°C in Kelvin
    }

    def __init__(self, id, type, name, credentials, p_type, s_unit):
        super().__init__(id, type, name)
        self.credentials = credentials
        self.scale_unit = s_unit
        self.product_type = p_type
        self.__state = None
        self.addTag('manufacturer', 'Dyson')

    def parseEnvironmentSensors(self, data) -> list:
        readings = list()
        time = data.get('time')
        data = data.get('data')
        if data.get('hact'):
            humidity = 0 if data.get('hact') == 'OFF' else int(data.get('hact'))
            readings.append((SEPL_SERVICE_HUM, humidity, '%', time))
        if data.get('vact'):
            volatile_compounds = 0 if data.get('vact') == 'INIT' else int(data.get('vact'))
            readings.append((SEPL_SERVICE_VOL, volatile_compounds, 'Number', time))
        if data.get('tact'):
            temperature = 0.0 if data.get('tact') == 'OFF' else round(float(data.get('tact')) / 10 - 273.15, 2)
            readings.append((SEPL_SERVICE_TEM, temperature, '°C', time))
        if data.get('pact'):
            dust = 0 if data.get('pact') == 'INIT' else int(data.get('pact'))
            readings.append((SEPL_SERVICE_DUS, dust, 'Amount', time))
        return readings

    def updateState(self, data):
        for state, value in data.items():
            self.__state[state] = value[1]

    @property
    def state(self):
        if self.__state:
            state = self.__state.copy()
            odd_keys = ['filf', 'fnst', 'ercd', 'wacd']
            missing_keys = {'sltm': 'STET', 'rstf': 'STET'}
            for key in odd_keys:
                try:
                    del state[key]
                except KeyError:
                    pass
            for key, value in missing_keys.items():
                state[key] = value
            return state

    @state.setter
    def state(self, arg):
        self.__state = arg

    def __repr__(self):
        return super().__repr__(credentials=self.credentials, product_type=self.product_type, state=self.__state, scale_unit=self.scale_unit)
