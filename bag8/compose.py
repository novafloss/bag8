from __future__ import absolute_import, print_function, unicode_literals

from bag8.common import PREFIX

from bag8.common import exec_
from bag8.common import simple_name
from bag8.common import Bag8Mixin
from bag8.common import get_temp_path
from bag8.common import json_check
from bag8.common import render_yml


class Figext(Bag8Mixin):

    def __init__(self, project, environment=None, links=None, ports=True,
                 reuseyml=False, user=None, volumes=None, no_volumes=False,
                 prefix=PREFIX):
        super(Figext, self).__init__(project=project)

        self.name = simple_name(self.project)
        self.no_volumes = no_volumes
        self.ports = ports
        self.reuseyml = reuseyml
        self.user = user

        environment, links, volumes = json_check(environment, links, volumes)
        self.environment = environment or {}
        self.links = links or []
        self.volumes = volumes or []
        self.prefix = prefix

    def call(self, action, extra_args=None):
        extra_args = extra_args if isinstance(extra_args, list) else []

        # generate yml file
        if not self.reuseyml:
            render_yml(self.project, environment=self.environment,
                       links=self.links, ports=self.ports, user=self.user,
                       volumes=self.volumes, no_volumes=self.no_volumes,
                       prefix=self.prefix)

        # we work in an insecure environment by default
        extra_args.insert(0, '--allow-insecure-ssl')

        # add custom options
        args = [
            '-f', get_temp_path(self.project, self.prefix),
            '-p', self.prefix,
            action,
        ] + extra_args

        # run command in a more simple way
        exec_('docker-compose {0}'.format(' '.join(args)))

    def run(self, command='bash'):
        self.call('run', [self.name, command])

    def up(self, daemon=False):
        args = ['--no-recreate']
        if daemon:
            args.append('-d')
        self.call('up', args)

    def pull(self):
        self.call('pull')
