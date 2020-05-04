import os
from pprint import pprint
from typing import Any, Dict, List, Optional, Union

from nornir.core.deserializer.inventory import Inventory, HostsDict


import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning


class NBExInventory(Inventory):
    def __init__(
        self,
        nb_url: Optional[str] = None,
        nb_token: Optional[str] = None,
        use_slugs: bool = True,
        ssl_verify: Union[bool, str] = True,
        flatten_custom_fields: bool = True,
        filter_parameters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
    Netbox Extended Plugin
    nb_url: Netbox url, defaults to http://localhost:8080.
    You can also use env variable NB_URL
    nb_token: Netbox token. You can also use env variable NB_TOKEN
    use_slugs: Whether to use slugs or not
    ssl_verify: Enable/disable certificate validation or provide path to CA bundle file
    flatten_custom_fields: Whether to assign custom fields directly to the host or not
    filter_parameters: Key-value pairs to filter down host
    """
        filter_parameters = filter_parameters or {}
        nb_url = nb_url or os.environ.get("NB_URL", "http://localhost:8080")
        nb_token = nb_token or os.environ.get(
            "NB_TOKEN", "66ce8c3ca355c1c4b262da2e44d16753521e7fb8"
        )

        nb_devices = self._fetch_data(
            nb_url=nb_url,
            ssl_verify=ssl_verify,
            nb_token=nb_token,
            filter_parameters=filter_parameters,
            devices=True,
        )
        hosts = {}
        for d in nb_devices:
            host: HostsDict = {"data": {}}

            # Add the value for IP address
            if d.get("primary_ip", {}):
                host["hostname"] = d["primary_ip"]["address"].split("/")[0]

            # Add the values that dont have an option for 'slug'
            host["data"]["serial"] = d["serial"]
            host["data"]["vendor"] = d["device_type"]["manufacturer"]["name"]
            host["data"]["asset_tag"] = d["asset_tag"]

            if flatten_custom_fields:
                for cf, value in d["custom_fields"].items():
                    host["data"][cf] = value
            else:
                host["data"]["custom_fields"] = d["custom_fields"]

            # Add values that have an option for 'slug'
            if use_slugs:
                host["data"]["site"] = d["site"]["slug"]
                host["data"]["role"] = d["device_role"]["slug"]
                host["data"]["model"] = d["device_type"]["slug"]

                # Attempt to add 'platform' based of value in slug
                host["platform"] = d["platform"]["slug"] if d["platform"] else None
            else:
                host["data"]["site"] = d["site"]["name"]
                host["data"]["role"] = d["device_role"]
                host["platform"] = d["platform"]

            # Get the IP addresses assigned to the interfaces of the host
            # host["data"]["interfaces"] = self._get_interfaces_IP(
            #     nb_url, ssl_verify, nb_token, d["id"]
            # )
            host["data"]["interfaces"] = self._get_host_interfaces(
                nb_url=nb_url, ssl_verify=ssl_verify, nb_token=nb_token, host_id=d["id"]
            )

            # Assign temporary dict to outer Dict
            # Netbos allows devices to be unnamed, but the Nornir model doesn't.
            # If a device is unnamed, set the name to the id of the device in netbox
            hosts[d.get("name") or d.get("id")] = host

        super().__init__(hosts=hosts, groups={}, defaults={}, **kwargs)

    def _fetch_data(
        self,
        nb_url=None,
        ssl_verify=True,
        nb_token=None,
        host_id=None,
        interface_id=None,
        filter_parameters=None,
        devices=False,
        interfaces=False,
        interfaces_ip=False,
    ):
        """
        Fetch data from Netbox API based on flags:
        devices=False - Fetch all devices from Netbox
        interfaces=False - Fetch akl interfaces data for a specific host
        interfaces_ip = False - Fetch all IP addresses for a specific interface on specific host
        devices, interfaces and interfaces_ip are mutually exclusive
        """
        results: List[Dict[str, Any]] = []
        if devices:
            url = f"{nb_url}/api/dcim/devices/?limit=0"
            interfaces = False
            interfaces_ip = False

        if interfaces_ip:
            url = f"{nb_url}/api/ipam/ip-addresses?device_id={host_id}&interface_id={interface_id}"
            interfaces = False
            devices = False

        if interfaces:
            url = f"{nb_url}/api/dcim/interfaces?device_id={host_id}"
            devices = False
            interfaces_ip = False

        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        session = requests.Session()
        session.headers.update({"Authorization": f"Token {nb_token}"})
        session.verify = ssl_verify

        # Fetch all deviced from Netbox
        # Netbox's API uses Pagination, Fetch until no nex

        while url:
            if devices:
                r = session.get(url, params=filter_parameters)
            else:
                r = session.get(url)

            if not r.status_code == 200:
                raise ValueError(
                    f"Failed to get the IP addresses from Netbox instance {nb_url}"
                )

            resp = r.json()
            results.extend(resp.get("results"))

            url = resp.get("next")
        return results

    def _get_host_interfaces(self, nb_url, ssl_verify, nb_token, host_id):

        interfaces_list = []
        interfaces = {}
        ip_interface_list = []

        interfaces_results = self._fetch_data(
            nb_url=nb_url,
            ssl_verify=ssl_verify,
            nb_token=nb_token,
            host_id=host_id,
            interfaces=True,
        )

        for interface_dict in interfaces_results:
            interfaces_list.append(interface_dict["name"])

        for interface in interfaces_list:
            for interface_dict in interfaces_results:
                if interface == interface_dict["name"]:
                    interfaces[interface] = {}
                    interfaces[interface]["IPv4"] = []
                    interfaces[interface]["IPv6"] = []
                    interfaces[interface]["id"] = interface_dict["id"]
                    # Check if interface is member of a LAG
                    if interface_dict["lag"] != None:
                        interfaces[interface]["lag"] = {}
                        interfaces[interface]["lag"]["name"] = interface_dict["lag"][
                            "name"
                        ]
                        interfaces[interface]["lag"]["id"] = interface_dict["lag"]["id"]

                    interfaces[interface]["mtu"] = interface_dict["mtu"]
                    interfaces[interface]["enabled"] = interface_dict["enabled"]
                    interfaces[interface]["description"] = interface_dict["description"]
                    # Get the Ip addresses for interfaces that have IP addresses defined in

                    if interface_dict["count_ipaddresses"] >= 1:
                        ip_results = self._fetch_data(
                            nb_url=nb_url,
                            ssl_verify=ssl_verify,
                            nb_token=nb_token,
                            host_id=host_id,
                            interface_id=interface_dict["id"],
                            interfaces_ip=True,
                        )

                        for intf_ip_dict in ip_results:
                            interface_ip_tuple = (
                                intf_ip_dict["address"],
                                intf_ip_dict["family"]["label"],
                                interface,
                            )
                            ip_interface_list.append(interface_ip_tuple)

                    for element in ip_interface_list:
                        if interface in element:
                            if "IPv4" in element:
                                interfaces[interface]["IPv4"].append(
                                    element[0])
                            else:
                                interfaces[interface]["IPv6"].append(
                                    element[0])

        return interfaces