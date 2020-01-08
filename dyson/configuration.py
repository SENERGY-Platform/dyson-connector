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


from simple_conf import configuration, section
import os


user_dir = '{}/storage'.format(os.getcwd())


@configuration
class DysonConf:

    @section
    class Account:
        email = None
        pw = None
        country = None

    @section
    class Cloud:
        host = "api.cp.dyson.com"
        auth_endpt = "v1/userregistration/authenticate?country="
        provisioning_endpt = "v1/provisioningservice/manifest"
        poll_interval = 300
        user = None
        pw = None

    @section
    class Discovery:
        interval = 240
        ports = "1883;8883"
        ping_timeout = 2
        probe_timeout = 2

    @section
    class RuntimeEnv:
        container = False

    @section
    class Logger:
        level = "info"

    @section
    class Senergy:
        dt_pure_cool_link = None


if not os.path.exists(user_dir):
    os.makedirs(user_dir)

config = DysonConf('dyson.conf', user_dir)


if not all((config.Account.email, config.Account.pw, config.Account.country)):
    exit('Please provide Dyson account credentials')

if not all((config.Cloud.host, config.Cloud.auth_endpt, config.Cloud.provisioning_endpt)):
    exit('Please provide Dyson Cloud information')

if not all((config.Senergy.dt_pure_cool_link, )):
    exit('Please provide SENERGY device types')
