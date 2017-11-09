try:
    from modules.logger import root_logger
    from dyson.session import SessionManager
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from socket import inet_ntoa as convert32bitToIp
from libpurecoollink.zeroconf import ServiceBrowser, Zeroconf, ServiceInfo


logger = root_logger.getChild(__name__)


class ServiceListener:
    def remove_service(self, zeroconf, type, name):
        logger.debug("service {} removed".format(name))
        SessionManager.delLocalDevice(name.split(".")[0].split("_")[1])

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        logger.debug("service {} added, service info: {}".format(name, info))
        logger.info("found local device with id '{}'".format(info.name.split(".")[0].split("_")[1]))
        SessionManager.addLocalDevice(info.name.split(".")[0].split("_")[1], convert32bitToIp(info.address), info.port)


browser = ServiceBrowser(Zeroconf(), "_dyson_mqtt._tcp.local.", ServiceListener())
