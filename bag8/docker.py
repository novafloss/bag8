from __future__ import absolute_import, print_function, unicode_literals

import click
import json
import os
from subprocess import check_output

from bag8.common import PREFIX
from bag8.common import TMPFOLDER

from bag8.common import call
from bag8.common import exec_
from bag8.common import Bag8Mixin
from bag8.common import get_container_name
from bag8.common import get_dockerfile_path
from bag8.common import get_image_name
from bag8.common import iter_deps
from bag8.common import iter_containers


class Dockext(Bag8Mixin):

    def __init__(self, container=None, prefix=PREFIX, project=None,
                 tag='latest'):
        super(Dockext, self).__init__(container=container, prefix=prefix,
                                      project=project)
        self.tag = tag

    @property
    def tmp_dockerfile_path(self):
        tmp_dockerfile_path = os.path.join(TMPFOLDER, self.project)
        if not os.path.exists(tmp_dockerfile_path):
            os.makedirs(tmp_dockerfile_path)
        return tmp_dockerfile_path

    @property
    def image(self):
        if not self.project:
            raise ValueError('No project.')
        return get_image_name(self.project, tag=self.tag)

    def build(self, force=False):
        dockerfile_path = get_dockerfile_path(self.project)
        exec_('docker build --rm {0} -t {1} {2}'.format(
            '' if not force else '--no-cache ', self.image, dockerfile_path))

    def commit(self):
        exec_('docker commit {0} {1}'.format(self.container, self.image))

    def cp(self, src, dest='.'):
        exec_('docker cp {0}:{1} {2}'.format(self.container, src, dest))

    def exec_(self, command='bash', interactive=False):
        exec_('docker exec {0} {1} {2}'.format('-it ' if interactive else '',
                                               self.container, command))

    def inspect(self):
        exec_('docker inspect {0}'.format(self.container))

    def inspect_live(self):
        out = check_output(['docker', 'inspect', self.container])
        return json.loads(out)

    def logs(self):
        exec_('docker logs -f {0}'.format(self.container))

    def pull(self):
        exec_('docker pull {0}'.format(self.image))

    def push(self):
        exec_('docker push {0}'.format(self.image))

    def rebuild(self):

        dockerfile_path = self.tmp_dockerfile_path

        with open(os.path.join(dockerfile_path, 'Dockerfile'), 'wb') as f:
            f.write("""
FROM {0}
""".format(self.image).strip())

        click.echo("""
Temporary Dockerfile to rebuild was generated here `{0}/Dockerfile`. Before
runnning `docker build` you can edit it and add some step.
""".strip().format(dockerfile_path))

        char = None
        while char not in ['c', 'q']:
            click.echo('Continue (c) or quit (q) ?')
            char = click.getchar()
            if char == 'c':
                break
            if char == 'q':
                return click.echo('quit.')

        exec_('docker build --rm -t {0} {1}'.format(self.image,
                                                    dockerfile_path))

    def rm(self, all=False):
        if all:
            containers = self.get_containers()
        else:
            containers = [self.container]
        for c in containers:
            call('docker rm -f {0}'.format(c))

    def rmi(self):
        exec_('docker rmi {0}'.format(self.image))

    def start(self, interactive=False, exit=True):

        # check deps
        for dep in iter_deps(self.project):
            # started
            if dep in [d for d in iter_containers(project=dep)]:
                continue
            # start dependency
            container = get_container_name(dep, prefix=self.prefix)
            call('docker start {0}'.format(container))

        call_func = exec_ if exit else call
        call_func('docker start {0} {1}'.format('-i ' if interactive else '',
                                                self.container))

    def stop(self):

        for dep in iter_deps(self.project):
            container = get_container_name(dep, prefix=self.prefix)
            call('docker stop {0}'.format(container))

        exec_('docker stop {0}'.format(self.container))
