from __future__ import absolute_import, division, print_function, unicode_literals  # noqa

import click
import os
import yaml


class Config(object):

    def __init__(self):
        # used in projects site.conf files and hosts command
        self.tmpfolder = os.path.expanduser('~/.local/bag8/')
        # load config
        self.config_path = os.path.expanduser('~/.config/bag8.yml')
        if os.path.exists(self.config_path):
            data = yaml.load(open(self.config_path))
        else:
            click.echo('No config found at: {0}.'.format(self.config_path))
            click.echo('Loads default values.')
            data = {}
        self.account = data.get('account', 'bag8')
        self.domain_suffix = data.get('domain_suffix', 'docker')
        self.insecure_registry = data.get('insecure_registry', False)
        self.prefix = data.get('prefix', 'bag8')
        self.registry = data.get('registry', None)
        self.docker_interface = data.get('docker_interface', 'docker0')
        self.docker_ip = data.get('docker_ip', '172.17.42.1')
        self._data_paths = [
            '.'  # current dir before all
        ] + data.get('data_paths', [])
        self.dnsdock_image = data.get('dnsdock_image',
                                      'tonistiigi/dnsdock:v1.10.0')

    def iter_data_paths(self):
        for p in self._data_paths:
            for d in os.listdir(p):
                if not os.path.exists(os.path.join(p, d, 'fig.yml')):
                    continue
                yield p, d

    @property
    def data_paths(self):
        return [p for p, d in self.iter_data_paths()]
