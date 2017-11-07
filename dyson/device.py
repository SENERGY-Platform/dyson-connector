try:
    from connector.device import Device
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))


dyson_map = {
    'N223': {
        'name': 'Dyson 360 Eye',
        'type': '',
        'tags': ('Vacuum', )
    },
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
        'type': '',
        'tags': ('Fan', 'Purifier')
    }
}


class DysonDevice(Device):
    def __init__(self, id, type, name, credentials, scale_unit):
        super().__init__(id, type, name)
        self.credentials = credentials
        self.scale_unit = scale_unit

    def __repr__(self):
        return super().__repr__(credentials=self.credentials, scale_unit=self.scale_unit)