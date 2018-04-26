try:
    from dyson.logger import root_logger
    from dyson.session import SessionManager
    from dyson.cloud_api_monitor import CloudApiMonitor
    from libpurecoollink.zeroconf import ServiceBrowser, Zeroconf
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from socket import inet_ntoa as convert32bitToIp
import time


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


def startDiscovery(init_time=30):
    browser = ServiceBrowser(Zeroconf(), "_dyson_mqtt._tcp.local.", ServiceListener())
    dyson_monitor = CloudApiMonitor()
    time.sleep(init_time)
    return browser, dyson_monitor
