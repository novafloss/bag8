from __future__ import absolute_import, division, print_function, unicode_literals  # noqa

import os
import yaml

from compose.cli.docker_client import docker_client
from compose.project import Project as ComposeProject
from compose.project import sort_service_dicts

from bag8.config import Config
from bag8.exceptions import NoDockerfile
from bag8.exceptions import NoProjectYaml
from bag8.service import Service
from bag8.utils import simple_name
from bag8.yaml import Yaml


class Project(ComposeProject):

    def __init__(self, name, develop=False):

        self.name = name

        self.config = Config()
        self.develop = develop

        self._services = []
        self._yaml = None

        super(Project, self).__init__(self.name, [], docker_client())

    @property
    def simple_name(self):
        return simple_name(self.name)

    @property
    def bag8_path(self):
        for path, _project in self.config.iter_data_paths():
            if _project == self.name:
                return os.path.join(path, _project)
        raise NoProjectYaml('missing dir for: {0}'.format(self.name))

    @property
    def temp_path(self):
        tmpfolder = self.config.tmpfolder
        if not os.path.exists(tmpfolder):
            os.makedirs(tmpfolder)
        return os.path.join(tmpfolder, '{0}.yml'.format(self.project))

    @property
    def yaml_path(self):
        return os.path.join(self.bag8_path, 'fig.yml')

    @property
    def site_conf_path(self):
        try:
            path = os.path.join(self.bag8_path, 'site.conf')
        except NoProjectYaml:
            return None
        if not os.path.exists(path):
            return None
        return path

    @property
    def build_path(self):
        if not os.path.exists(os.path.join(self.bag8_path, 'Dockerfile')):
            raise NoDockerfile('missing Dockerfile for: {0}'.format(self.name))
        return self.bag8_path

    @property
    def yaml(self):
        if not self._yaml:
            self._yaml = yaml.load(open(self.yaml_path))
        return self._yaml

    @property
    def image(self):
        return self.yaml.get('app', {}).get('image', None)

    @property
    def links(self):
        """Returns links from the app section of the project yaml file.
        """
        return [l.split(':')[0]
                for l in self.yaml.get('app', {}).get('links', [])]

    @property
    def internal_links(self):
        """Returns links from the project yaml file but not in the app section.
        """
        return [s for s in self.yaml.keys() if s != 'app']

    @classmethod
    def iter_projects(cls):
        for c in docker_client().containers():
            name = c['Labels'].get('com.docker.compose.service')
            # not a compose project
            if not name:
                continue
            yield Project(name)

    def iter_deps_names(self, _wrap=True):

        if _wrap:
            # uniqify deps
            for p in set([p for p in self.iter_deps_names(_wrap=False)]):
                yield p
            raise StopIteration()

        for link in self.links:
            if link in self.internal_links:
                continue
            link_project = Project(link)
            for sub_link in link_project.iter_deps_names(_wrap=False):
                yield sub_link
            yield link

    @property
    def deps_names(self):
        return [n for n in self.iter_deps_names()]

    @property
    def deps(self):
        return [Project(n) for n in self.deps_names]

    @classmethod
    def from_dicts(cls, name, service_dicts, client):
        """Overrides compose method to use custom service class
        """
        project = cls(name)
        for service_dict in sort_service_dicts(service_dicts):
            links = project.get_links(service_dict)
            volumes_from = project.get_volumes_from(service_dict)
            net = project.get_net(service_dict)
            project._services.append(Service(client=client,
                                             project=name,
                                             links=links,
                                             net=net,
                                             volumes_from=volumes_from,
                                             **service_dict))
        return project

    @property
    def services(self):
        if not self._services:
            _yaml = Yaml(self)
            self._services = Project.from_dicts(self.name,
                                                _yaml.service_dicts,
                                                self.client).services
        return self._services

    @services.setter
    def services(self, value):
        """Hacks default services setter.
        """
        pass

    def push(self, service_names=None, insecure_registry=False):
        for service in self.get_services(service_names):
            service.push(insecure_registry=insecure_registry)

    def rmi(self, service_names=None, force=False):
        for service in self.get_services(service_names):
            service.rmi(force=force)

    def run(self, **options):
        service = self.get_service(self.simple_name)
        deps = service.get_linked_names()
        if len(deps) > 0:
            self.up(
                service_names=deps,
                start_deps=True,
                allow_recreate=False,
                insecure_registry=options.get('insecure_registry'),
            )
        service.run(**options)

    def start(self, service_names=None, interactive=False, **options):
        service = self.get_service(self.simple_name)
        deps = service.get_linked_names()
        for dep_service in self.get_services(service_names):
            if dep_service.name not in deps:
                continue
            dep_service.start(**options)
        service.start(interactive=interactive, **options)

    def execute(self, service_name=None, **options):
        service = self.get_service(service_name or self.simple_name)
        service.execute(**options)
