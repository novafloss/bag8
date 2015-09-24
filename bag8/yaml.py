from __future__ import absolute_import, division, print_function

import click
import os
import yaml

from bag8.exceptions import NoProjectYaml
from bag8.utils import simple_name


class Yaml(object):

    def __init__(self, project):
        self.project = project
        self._data = None
        self._bag8_names = {}

    def _get_customized_yml(self, project):
        """Prefixes project sections with project name, ex: pg > busyboxpg.
        """

        custom_yml = {}

        try:
            __ = project.yaml_path  # noqa
        except NoProjectYaml as e:
            click.echo(e.message)
            return custom_yml

        for k, v in yaml.load(open(project.yaml_path)).items():

            # ensure environment for coming overinding
            if 'environment' not in v:
                v['environment'] = {}
            # ensure common env section format -> list
            elif isinstance(v['environment'], list):
                v['environment'] = dict([l.split('=')
                                         for l in v['environment']])

            # shortcuts
            name = k if k != 'app' else project.simple_name
            domain_suffix = project.config.domain_suffix
            domainname = v.get('domainname',
                               '{0}.{1}'.format(name, domain_suffix))
            if 'DNSDOCK_ALIAS' not in v['environment']:
                v['environment']['DNSDOCK_ALIAS'] = domainname
            v['environment']['DNSDOCK_IMAGE'] = ''

            # update sections
            custom_yml[name] = v

            links = []
            for link in v.get('links', []):
                try:
                    _, name = link.split(':', 1)
                except ValueError:
                    name = link
                links.append(name)
            v['environment']['BAG8_LINKS'] = ' '.join(links)

        return custom_yml

    def _update_yml_dict(self, yml_dict, project):

        for p in project.deps:
            yml_dict = self._update_yml_dict(yml_dict, p)

        yml_dict.update(self._get_customized_yml(project))

        return yml_dict

    def render(self):

        self._data = self._update_yml_dict({}, self.project)

        # ensure good app name
        app = self.project.simple_name

        # keep bag8 name mapping
        self._bag8_names[app] = self.project.bag8_name

        # clean links according tree permitted names and project accepted ones,
        # ex.: dummy.js:dummyjs.docker > dummyjs:dummyjs.docker
        links = []
        for link in self._data[app].get('links', []):
            bag8_name = link.split(':')[0]
            name = simple_name(bag8_name)
            self._bag8_names[name] = bag8_name
            link = name + ':' + link.split(':')[1] if ':' in link else name
            links.append(link)
        self._data[app]['links'] = links

        # ensure environment for coming overinding
        if 'environment' not in self._data[app]:
            self._data[app]['environment'] = {}
        # ensure common env section format -> list
        elif isinstance(self._data[app]['environment'], list):
            self._data[app]['environment'] = \
                dict([l.split('=') for l in self._data[app]['environment']])

        # Setup develop mode
        if self.project.develop:
            for volume in self._data[app].get('dev_volumes', []):
                if 'volumes' not in self._data[app]:
                    self._data[app]['volumes'] = []
                self._data[app]['volumes'].append(volume % os.environ)

            dev_environment = self._data[app].get('dev_environment', {})
            if isinstance(dev_environment, list):
                dev_environment = dict([l.split('=') for l in dev_environment])
            self._data[app]['environment'].update(dev_environment)

            if 'dev_command' in self._data[app]:
                self._data[app]['command'] = self._data[app]['dev_command']

        # Clean compose extensions
        for key in self._data:
            for k in ['dev_command', 'dev_environment', 'dev_volumes']:
                if k in self._data[key]:
                    del self._data[key][k]

        # add dockerfile info for build
        self._data[app]['dockerfile'] = os.path.join(self.project.bag8_path,
                                                     'Dockerfile')

    @property
    def data(self):
        if not self._data:
            self.render()
        return self._data

    @property
    def service_dicts(self):
        service_dicts = []
        for k, v in self.data.items():
            v['name'] = k
            v['bag8_name'] = self._bag8_names.get(k)
            service_dicts.append(v)
        return service_dicts

    def write(self):
        # write to tmp path
        with open(self.project.temp_path, 'wb') as out_yml:
            out_yml.write(yaml.safe_dump(self.data))
