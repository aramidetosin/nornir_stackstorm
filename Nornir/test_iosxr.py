from nornir import InitNornir
from nornir.plugins.tasks import networking, text
from nornir.plugins.functions.text import print_result

nr = InitNornir(config_file='config.yaml', dry_run=True)
matched_devices = nr.filter(platform='iosxr')

cmd = ["show version", "sh ip int brief"]
for command in cmd:
    result = matched_devices.run(
        networking.netmiko_send_command, command_string=command)
    print_result(result)

result2 = matched_devices.run(task=networking.napalm_get, getters=['facts'])


print_result(result2)
