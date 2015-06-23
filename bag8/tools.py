from __future__ import absolute_import, print_function, unicode_literals

import click
import os
import shutil

from compose.cli.docker_client import docker_client

from docker.errors import APIError

from bag8.common import DOCKER_IP
from bag8.common import DOMAIN_SUFFIX
from bag8.common import PREFIX
from bag8.common import TMPFOLDER

from bag8.common import call
from bag8.common import confirm
from bag8.common import write_conf
from bag8.common import simple_name
from bag8.common import get_available_projects
from bag8.common import get_container_name
from bag8.common import get_bag8_path
from bag8.common import get_site_projects
from bag8.common import inspect
from bag8.common import iter_containers
from bag8.common import json_check
from bag8.common import render_yml


class Tools(object):

    def __init__(self, project=None):
        self.project = project

    def _update_resolve_conf(self):

        conf_path = '/etc/resolvconf/resolv.conf.d/head'
        conf_entry = 'nameserver\t{0}'.format(DOCKER_IP)
        conf_content = []

        # check already set
        with open(conf_path) as f:
            conf_content += [l.strip() for l in f.readlines()]

        if [l for l in conf_content if DOCKER_IP in l]:
            return
        conf_content.append(conf_entry)

        click.echo("""
# updates {0} with:
{1}
""".format(conf_path, conf_entry))

        # update resolve config
        write_conf(conf_path, '\n'.join(conf_content) + '\n',
                   bak_path='/tmp/resolv.conf.d_head.orig')

        if confirm('`sudo resolvconf -u` ?'):
            call('sudo resolvconf -u')

    def hosts(self):

        self._update_resolve_conf()

        # not running
        try:
            if not inspect('dnsdock')['State']['Running']:
                call(' '.join([
                    'docker',
                    'start',
                    'dnsdock',
                ]))
        # not exist
        except APIError:
            call(' '.join([
                'docker',
                'run',
                '-d',
                '-v /var/run/docker.sock:/var/run/docker.sock',
                '--name dnsdock',
                '-p 172.17.42.1:53:53/udp',
                'tonistiigi/dnsdock',
                "-domain={0}".format(DOMAIN_SUFFIX)
            ]))

    def projects(self):
        click.echo('\n'.join(get_available_projects()))

    def nginx(self, links=None, volumes=None):

        conf_path = os.path.join(TMPFOLDER, 'nginx', 'conf.d')
        # remove previous configs
        shutil.rmtree(conf_path, ignore_errors=True)
        # create new conf folder
        os.makedirs(conf_path)

        log_path = os.path.join(TMPFOLDER, 'nginx', 'log')
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        environment, links, volumes = json_check(None, links, volumes)

        links = ['{0}:{1}'.format(get_container_name(l.split(':')[0]),
                                  l.split(':')[1]) for l in links]

        volumes += [
            '{0}:/etc/nginx/conf.d'.format(conf_path),
            '{0}:/var/log/nginx'.format(log_path),
        ]

        containers = {n.split('_')[1]: n
                      for n, __ in iter_containers()}
        dnsdock_alias = []
        volumes_from = []

        for project in get_site_projects(running=True):
            # shortcut
            name = simple_name(project)
            container_name = containers[name]
            # update alias
            dnsdock_alias.append('{0}.nginx.{1}'.format(name, DOMAIN_SUFFIX))
            # updates volumes from to share between site and nginx containers
            volumes_from.append(container_name)
            # add link to nginx
            links.append('{0}:{1}.local'.format(container_name, name))
            # copy nginx site conf
            shutil.copy(os.path.join(get_bag8_path(project), 'site.conf'),
                        os.path.join(conf_path, '{0}.conf'.format(project)))

        docker_args = [
            'docker',
            'run',
            '-d',
            '-e DNSDOCK_ALIAS={0}'.format(','.join(dnsdock_alias)),
            '--name {0}_nginx_1'.format(PREFIX),  # TODO get prefix from cli
            '-p', '0.0.0.0:80:80',
            '-p', '0.0.0.0:443:443',
            '--hostname www.nginx.local',
            ' '.join(['--volumes-from {0}'.format(v) for v in volumes_from]),
            ' '.join(['-v {0}'.format(v) for v in volumes]),
            ' '.join(['--link {0}'.format(l) for l in links]),
            'nginx',
        ]

        return call(' '.join(docker_args))

    def render(self, environment, links, ports, user, volumes, no_volumes,
               prefix, develop):

        environment, links, volumes = json_check(environment, links, volumes)

        render_yml(self.project, environment=environment, links=links,
                   ports=ports, user=user, volumes=volumes,
                   no_volumes=no_volumes, prefix=prefix,
                   develop=develop)
