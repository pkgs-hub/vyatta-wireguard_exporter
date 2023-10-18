#!/usr/bin/env python3
import os

from sys import exit

from vyos.config import Config
from vyos.configdict import dict_merge
from vyos.configverify import verify_vrf
from vyos.util import call
from vyos.template import render
from vyos import ConfigError
from vyos import airbag
from jinja2 import Template


airbag.enable()

config_file = r'/etc/default/wireguard_exporter'

def get_config(config=None):
    if config:
        conf = config
    else:
        conf = Config()
    base = ['service', 'monitoring', 'wireguard-exporter']
    if not conf.exists(base):
        return None

    wireguard_exporter = conf.get_config_dict(base, get_first_key=True)

    return wireguard_exporter

def verify(wireguard_exporter):
    if wireguard_exporter is None:
        return None
    
    verify_vrf(wireguard_exporter)
    return None

def generate(wireguard_exporter):
    if wireguard_exporter is None:
        if os.path.isfile(config_file):
            os.unlink(config_file)
        return None

    # merge web/listen-address with subelement web/listen-address/port
    # {'web': {'listen-address': {'0.0.0.0': {'port': '8080'}}}
    if 'web' in wireguard_exporter and 'listen-address' in wireguard_exporter['web']:
        address = list(wireguard_exporter['web']['listen-address'].keys())[0]
        port = wireguard_exporter['web']['listen-address'][address].get("port", 9100)
        wireguard_exporter['web']['listen-address'] = f"{address}:{port}"

    # remove empty elements
    #wireguard_exporter = {key: value for key, value in wireguard_exporter.items() if value}

    with open('/opt/vyatta-wireguard_exporter/config.j2', 'r') as tmpl, open(config_file, 'w') as out:
        template = Template(tmpl.read()).render(data=wireguard_exporter)
        out.write(template)

    # Reload systemd manager configuration
    call('systemctl daemon-reload')

    return None

def apply(wireguard_exporter):
    if wireguard_exporter is None:
        # wireguard_exporter is removed in the commit
        call('systemctl stop wireguard_exporter.service')
        return None

    call('systemctl restart wireguard_exporter.service')
    return None

if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        exit(1)
