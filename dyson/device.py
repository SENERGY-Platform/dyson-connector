try:
    from modules.logger import root_logger
    from connector.device import Device
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json


logger = root_logger.getChild(__name__)


class DysonDevice(Device):
    def __init__(self, id, type, name, credentials, p_type, s_unit):
        super().__init__(id, type, name)
        self.credentials = credentials
        self.scale_unit = s_unit
        self.product_type = p_type
        self.addTag('manufacturer', 'Dyson')

    def getEnvironmentSensors(self, data) -> list:
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

    def __repr__(self):
        return super().__repr__(credentials=self.credentials, scale_unit=self.scale_unit)


class DysonPureHotCoolLink(DysonDevice):
    def __init__(self, id, credentials, p_type, s_unit):
        super().__init__(id, '', 'Dyson Pure Hot + Cool Link', credentials, p_type, s_unit)
        self.addTag('type', 'Fan')
        self.addTag('type1', 'Heater')
        self.addTag('type2', 'Purifier')


class DysonPureCooLinkDesk(DysonDevice):
    def __init__(self, id, credentials, p_type, s_unit):
        super().__init__(id, '', 'Dyson Pure Cool Link Desk', credentials, p_type, s_unit)
        self.addTag('type', 'Fan')
        self.addTag('type1', 'Purifier')


class DysonPureCoolLink(DysonDevice):
    def __init__(self, id, credentials, p_type, s_unit):
        super().__init__(id, '', 'Dyson Pure Cool Link', credentials, p_type, s_unit)
        self.addTag('type', 'Fan')
        self.addTag('type1', 'Purifier')


dyson_map = {
    '455': DysonPureHotCoolLink,
    '469': DysonPureCooLinkDesk,
    '475': DysonPureCoolLink
}