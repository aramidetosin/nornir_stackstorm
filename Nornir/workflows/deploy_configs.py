import sys
from nornir import InitNornir
from nornir.plugins.tasks import networking, text
from nornir.plugins.functions.text import print_result


def basic_configuration(task, template_name=None):
    r = task.run(task=text.template_file,
                 name="Base Configuration",
                 template=template_name,
                 path=f"../templates/{task.host.platform}")

    task.host["config"] = r.result

    task.run(task=networking.napalm_configure, name="Loading Configuration on the device",
             replace=False, configuration=task.host["config"])


def main():
    templ_name = sys.argv[1]
    platform = sys.argv[1]
    nr = InitNornir(config_file='../config.yaml', dry_run=True)
    matched_devices = nr.filter(platform=platform)
    result = matched_devices.run(
        task=basic_configuration, template_name=templ_name)
    # result_facts = matched_devices.run(
    #     task=networking.napalm_get, getters=['facts'])
    print_result(result)
    # print_result(result_facts)


if __name__ == "__main__":
    main()
