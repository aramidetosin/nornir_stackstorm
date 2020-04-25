from nornir import InitNornir
from nornir.plugins.tasks import networking, text
from nornir.plugins.functions.text import print_result
import logging
from pprint import pprint as pp

nr = InitNornir(config_file='config.yaml', dry_run=True)
matched_devices = nr.filter(platform='junos')
matched_devices_ios = nr.filter(platform='ios')

# cmd = ["show version", "sh ip int brief"]
# for command in cmd:
#     result = matched_devices.run(
#         networking.netmiko_send_command, command_string=command)
#     print_result(result)

# result2 = matched_devices.run(task=networking.napalm_get, getters=["facts",
#                                                                    "interfaces"], severity_level=logging.INFO)

# method_list = [func for func in dir(result2) if callable(
#     getattr(result2, func)) and not func.startswith("_")]

# for method in method_list:
#     print(f"result2.{method}()")

result3 = matched_devices.run(
    task=networking.napalm_get, getters=["interfaces_ip"])

result_ios = matched_devices_ios.run(
    task=networking.napalm_get, getters=["interfaces_ip"])
# print_result(result2['r1'][0])
# print_result(result2)
print_result(result3)
print_result(result_ios)

# print_result(result2.items())
