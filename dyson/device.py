try:
    from modules.logger import root_logger
    from connector.device import Device
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json


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
        'type': 'iot#2b7534de-c2d9-4f5c-a6a0-9e3b21a09f02',
        'tags': ('Fan', 'Purifier')
    }
}



class DysonDevice(Device):
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
            readings.append(('humidity service', humidity, time))
        if data.get('vact'):
            volatile_compounds = 0 if data.get('vact') == 'INIT' else int(data.get('vact'))
            readings.append(('volatile_compounds service', volatile_compounds, time))
        if data.get('tact'):
            temperature = 0 if data.get('tact') == 'OFF' else float(data.get('tact'))/10
            readings.append(('temperature service', temperature, time))
        if data.get('pact'):
            dust = 0 if data.get('pact') == 'INIT' else int(data.get('pact'))
            readings.append(('dust service', dust, time))
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
