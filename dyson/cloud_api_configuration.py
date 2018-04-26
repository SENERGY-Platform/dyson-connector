try:
    from dyson.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import os, inspect, configparser


logger = root_logger.getChild(__name__)


dyson_account_email = 'smart.energy.platform@gmail.com'
dyson_account_pw = 'connector1!'
dyson_account_country = 'DE'


config = configparser.ConfigParser()
conf_file_path = '{}/cloud_api.conf'.format(os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0])))


if not os.path.isfile(conf_file_path):
    config['DYSON_ACCOUNT'] = {
        'email': dyson_account_email,
        'pw': dyson_account_pw,
        'country': dyson_account_country
    }
    config['CLOUD_API'] = {
        'url': 'api.cp.dyson.com',
        'user': '',
        'pw': '',
    }
    with open(conf_file_path, 'w') as conf_file:
        config.write(conf_file)


try:
    config.read(conf_file_path)
except Exception as ex:
    exit(ex)


def writeConf(section, option, value):
    config.set(section=section, option=option, value=value)
    try:
        with open(conf_file_path, 'w') as conf_file:
            config.write(conf_file)
    except Exception as ex:
        print(ex)


DYSON_ACCOUNT_EMAIL = config['DYSON_ACCOUNT']['email']
DYSON_ACCOUNT_PW = config['DYSON_ACCOUNT']['pw']
DYSON_ACCOUNT_COUNTRY = config['DYSON_ACCOUNT']['country']
DYSON_CLOUD_API_URL = config['CLOUD_API']['url']
DYSON_CLOUD_API_USER = config['CLOUD_API']['user']
DYSON_CLOUD_API_PW = config['CLOUD_API']['pw']