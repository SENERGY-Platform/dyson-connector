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

try:
    from dyson.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import os, inspect, configparser


logger = root_logger.getChild(__name__)

conf_path = os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])
conf_file = 'dyson.conf'

config = configparser.ConfigParser()



if not os.path.isfile(os.path.join(conf_path, conf_file)):
    print('No config file found')
    config['DYSON_ACCOUNT'] = {
        'email': '',
        'pw': '',
        'country': ''
    }
    config['DYSON_API'] = {
        'url': 'api.cp.dyson.com',
        'user': '',
        'pw': '',
    }
    config['SEPL'] = {
        'device_type': '',
        'device_service_humidity': '',
        'device_service_volatile': '',
        'device_service_temperature': '',
        'device_service_dust': ''
    }
    with open(os.path.join(conf_path, conf_file), 'w') as conf_file:
        config.write(conf_file)
    exit("Created blank config file at '{}'".format(conf_path))


try:
    config.read(os.path.join(conf_path, conf_file))
except Exception as ex:
    exit(ex)


def writeConf(section, option, value):
    config.set(section=section, option=option, value=value)
    try:
        with open(os.path.join(conf_path, conf_file), 'w') as cf:
            config.write(cf)
    except Exception as ex:
        print(ex)


DYSON_ACCOUNT_EMAIL = config['DYSON_ACCOUNT']['email']
DYSON_ACCOUNT_PW = config['DYSON_ACCOUNT']['pw']
DYSON_ACCOUNT_COUNTRY = config['DYSON_ACCOUNT']['country']
DYSON_CLOUD_API_URL = config['DYSON_API']['url']
DYSON_CLOUD_API_USER = config['DYSON_API']['user']
DYSON_CLOUD_API_PW = config['DYSON_API']['pw']
SEPL_DEVICE_TYPE = config['SEPL']['device_type']
SEPL_SERVICE_HUM = config['SEPL']['device_service_humidity']
SEPL_SERVICE_VOL = config['SEPL']['device_service_volatile']
SEPL_SERVICE_TEM = config['SEPL']['device_service_temperature']
SEPL_SERVICE_DUS = config['SEPL']['device_service_dust']

if not all((DYSON_ACCOUNT_EMAIL, DYSON_ACCOUNT_PW, DYSON_ACCOUNT_COUNTRY)):
    exit('Please provide Dyson account credentials')

if not DYSON_CLOUD_API_URL:
    exit('Please provide Dyson cloud API credentials')

if not all((SEPL_DEVICE_TYPE, SEPL_SERVICE_HUM, SEPL_SERVICE_VOL, SEPL_SERVICE_TEM, SEPL_SERVICE_DUS)):
    exit('Please provide SEPL device type and services')
