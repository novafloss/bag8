from __future__ import absolute_import, division, print_function

import os
import shlex
import sys

import click

import dockerpty

from docker.errors import APIError

from compose.container import Container
from compose.progress_stream import stream_output
from compose.service import Service as ComposeService
from compose.service import parse_repository_tag

from bag8.config import Config
from bag8.const import LABEL_BAG8_PROJECT
from bag8.const import LABEL_BAG8_SERVICE
from bag8.utils import exec_, wait_


class Service(ComposeService):

    def __init__(self, name, bag8_name='', bag8_project='', image_name=None,
                 **kwargs):
        super(Service, self).__init__(name, **kwargs)
        self.bag8_name = bag8_name
        self.bag8_project = bag8_project
        # hack to propagate build path and image name
        if 'dockerfile' in self.options:
            self.options['build'] = os.path.dirname(self.options['dockerfile'])
            del self.options['dockerfile']

    def containers(self, stopped=False, one_off=False, bag8_labels=False):
        return [
            Container.from_ps(self.client, container)
            for container in self.client.containers(
                all=stopped,
                filters={'label': self.labels(one_off=one_off,
                                              bag8_labels=bag8_labels)})]

    def labels(self, one_off=False, bag8_labels=True):
        labels = super(Service, self).labels(one_off=one_off)
        if not bag8_labels:
            return labels
        return labels + [
            '{0}={1}'.format(LABEL_BAG8_PROJECT, self.bag8_project),
            '{0}={1}'.format(LABEL_BAG8_SERVICE, self.bag8_name),
        ]

    @property
    def image_name(self):
        return self.options['image']

    def build(self, no_cache=False):
        super(Service, self).build(no_cache=no_cache)

    def rmi(self, force=False):
        try:
            self.client.remove_image(self.image_name, force)
        except APIError as e:
            # not a 404 error
            if not hasattr(e, 'response') or e.response.status_code != 404:
                raise e
            click.echo('image not found: {0}'.format(self.image_name))

    def push(self, insecure_registry=False):
        if 'image' not in self.options:
            return
        repo, tag = parse_repository_tag(self.options['image'])
        tag = tag or 'latest'
        click.echo('Pushing %s (%s:%s)...' % (self.name, repo, tag))
        output = self.client.push(
            repo,
            tag=tag,
            stream=True,
            insecure_registry=insecure_registry)
        stream_output(output, sys.stdout)

    def run(self, command=None, detach=False, insecure_registry=False,
            interactive=True, remove=False, tty=None):

        if command is None:
            command = self.options.get('command')

        if tty is None:
            tty = sys.stdin.isatty()

        container = self.create_container(
            command=command,
            detach=detach,
            insecure_registry=insecure_registry,
            quiet=True,
            one_off=False,
            stdin_open=not detach,
            tty=tty,
        )

        dockerpty.start(self.client, container.id, interactive=interactive)
        exit_code = container.wait()

        if remove:
            self.client.remove_container(container.id)

        sys.exit(exit_code)

    def wait_links(self):
        config = Config()
        for service, name in self.links:
            for ports in service.options.get('expose', []):
                if not ports:
                    continue
                host = '{}.{}'.format(service.bag8_name, config.domain_suffix)
                port_to_wait = str(ports).split(':')[0]
                wait_(host, port_to_wait, max_retry=config.wait_seconds)

    def start(self, one_off=False, **options):
        for c in self.containers(stopped=True, one_off=one_off):
            self.start_container_if_stopped(c, **options)

    def start_container_if_stopped(self, container, **options):
        if container.is_running:
            return container
        else:
            return self.start_container(container, **options)

    def start_container(self, container, **options):
        interactive = options.pop('interactive', False)
        self.wait_links()
        if interactive:
            dockerpty.start(self.client, container.id, interactive=interactive)
            exit_code = container.wait()
            sys.exit(exit_code)
        else:
            container.start(**options)
        return container

    def execute(self, one_off=False, **options):
        for c in self.containers(one_off=one_off):
            self.execute_container(c, **options)

    def execute_container(self, container, command=None, interactive=True,
                          tty=sys.stdin.isatty()):
        args = ['docker', 'exec']
        if interactive:
            args += ['-i']
        if tty:
            args += ['-t']
        args += [
            container.name,
        ]
        args += shlex.split(command or self.options.get('command'))
        return exec_(args)
