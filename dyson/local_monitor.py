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
from .device_manager import DeviceManager
# from .session import SessionManager
from libpurecoollink.zeroconf import ServiceBrowser, Zeroconf, get_all_addresses
import time, threading, cc_lib, socket, os, platform, subprocess


logger = root_logger.getChild(__name__.split(".", 1)[-1])


def ping(host) -> bool:
    return subprocess.call(['ping', '-c', '2', '-t', str(config.Discovery.ping_timeout), host], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def getLocalIP() -> str:
    try:
        if config.RuntimeEnv.container:
            host_ip = os.getenv("HOST_IP")
            if not host_ip:
                raise Exception("environment variable 'HOST_IP' not set")
            return host_ip
        else:
            sys_type = platform.system().lower()
            if 'linux' in sys_type:
                local_ip = subprocess.check_output(['hostname', '-I']).decode()
                local_ip = local_ip.replace(' ', '')
                local_ip = local_ip.replace('\n', '')
                return local_ip
            elif 'darwin' in sys_type:
                local_ip = socket.gethostbyname(socket.getfqdn())
                if type(local_ip) is str and local_ip.count('.') == 3:
                    return local_ip
            else:
                raise Exception("platform not supported")
    except Exception as ex:
        logger.critical("could not get local ip - {}".format(ex))

def getIpRange(local_ip) -> list:
    split_ip = local_ip.rsplit('.', 1)
    base_ip = split_ip[0] + '.'
    if len(split_ip) > 1:
        ip_range = [str(base_ip) + str(i) for i in range(2,255)]
        ip_range.remove(local_ip)
        return ip_range
    return list()

def discoverHostsWorker(ip_range, alive_hosts):
    for ip in ip_range:
        if ping(ip):
            alive_hosts.append(ip)

def discoverHosts() -> list:
    alive_hosts = list()
    host_ip = getLocalIP()
    if host_ip:
        ip_range = getIpRange(host_ip)
        workers = list()
        bin = 0
        bin_size = 3
        if ip_range:
            for i in range(int(len(ip_range) / bin_size)):
                worker = threading.Thread(target=discoverHostsWorker, name='discoverHostsWorker', args=(ip_range[bin:bin+bin_size], alive_hosts), daemon=True)
                workers.append(worker)
                worker.start()
                bin = bin + bin_size
            if ip_range[bin:]:
                worker = threading.Thread(target=discoverHostsWorker, name='discoverHostsWorker', args=(ip_range[bin:], alive_hosts), daemon=True)
                workers.append(worker)
                worker.start()
            for worker in workers:
                worker.join()
    return alive_hosts

def probeHost(host) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(config.Discovery.probe_timeout)
    try:
        s.connect((host, config.Discovery.port))
        s.close()
        return True
    except (ConnectionError, TimeoutError, socket.timeout):
        return False

def validateHostsWorker(hosts, valid_hosts):
    for host in hosts:
        hostname = socket.getfqdn(host)
        if hostname and hostname is not host and probeHost(host):
            valid_hosts[hostname.upper().split(".", 1)[0]] = host

def validateHosts(hosts) -> dict:
    valid_hosts = dict()
    workers = list()
    bin = 0
    bin_size = 2
    if len(hosts) <= bin_size:
        worker = threading.Thread(target=validateHostsWorker, name='validateHostsWorker', args=(hosts, valid_hosts), daemon=True)
        workers.append(worker)
        worker.start()
    else:
        for i in range(int(len(hosts) / bin_size)):
            worker = threading.Thread(target=validateHostsWorker, name='validateHostsWorker', args=(hosts[bin:bin + bin_size], valid_hosts), daemon=True)
            workers.append(worker)
            worker.start()
            bin = bin + bin_size
        if hosts[bin:]:
            worker = threading.Thread(target=validateHostsWorker, name='validateHostsWorker', args=(hosts[bin:], valid_hosts), daemon=True)
            workers.append(worker)
            worker.start()
    for worker in workers:
        worker.join()
    return valid_hosts

def diff(known: dict, unknown: dict):
    known_set = set(known)
    unknown_set = set(unknown)
    missing = known_set - unknown_set
    new = unknown_set - known_set
    changed = {key for key in known_set & unknown_set if known[key] != unknown[key]}
    return missing, new, changed


class LocalMonitor(threading.Thread):
    def __init__(self, device_manager: DeviceManager, client: cc_lib.client.Client):
        super().__init__(name=__class__.__name__, daemon=True)
        self.__device_manager = device_manager
        self.__client = client
        self.__devices_cache = dict()

    def run(self) -> None:
        while True:
            devices = self.__discoverDevices()
            self.__evaluate(devices)
            time.sleep(config.Discovery.delay)

    # def remove_service(self, zeroconf, type, name):
    #     pass
    #     # SessionManager.delLocalDevice(name.split(".")[0].split("_")[1])
    #
    # def add_service(self, zeroconf, type, name):
    #     info = zeroconf.get_service_info(type, name)
    #     device_id = info.name.split(".")[0].split("_")[1]
    #     device_ip = socket.inet_ntoa(info.address)
    #     device_port = info.port
    #     logger.debug("discovered '{}': {}".format(name, info))
    #     self.__devices_buffer[device_id] = {
    #         "ip": device_ip,
    #         "port": device_port
    #     }
    #     # logger.info("found local device with id '{}' on '{}:{}'".format(device_id, device_ip, device_port))
    #     # SessionManager.addLocalDevice(info.name.split(".")[0].split("_")[1], device_ip, device_port)

    # def __discoverDevices(self):
    #     logger.debug("running local device discovery for {}s".format(config.Local.discovery_duration))
    #     zeroconf = Zeroconf()
    #     service_browser = ServiceBrowser(zeroconf, "_dyson_mqtt._tcp.local.", self)
    #     time.sleep(config.Local.discovery_duration)
    #     zeroconf.close()
    #     service_browser.join()
    #     logger.debug("local device discovery completed")

    def __discoverDevices(self):
        logger.debug("running device discovery ...")
        hosts = validateHosts(discoverHosts())
        registered_ids = self.__device_manager.devices.keys()
        devices = {id: hosts[id] for id in registered_ids if id in hosts}
        logger.debug("device discovery completed")
        return devices

    def __evaluate(self, discovered_devices):
        logger.debug("cache: {}, discovered: {}".format(self.__devices_cache, discovered_devices))
        missing_devices, new_devices, changed_devices = diff(self.__devices_cache, discovered_devices)
        if missing_devices:
            for device_id in missing_devices:
                logger.info("can't find '{}' at '{}'".format(device_id, self.__devices_cache[device_id]))
        if new_devices:
            for device_id in new_devices:
                logger.info("found '{}' at '{}'".format(device_id, discovered_devices[device_id]))
        if changed_devices:
            for device_id in changed_devices:
                logger.info("address of '{}' changed to '{}'".format(device_id, discovered_devices[device_id]))
        if any((missing_devices, new_devices, changed_devices)):
            self.__devices_cache = discovered_devices
