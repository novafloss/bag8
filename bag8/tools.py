from __future__ import absolute_import, print_function, unicode_literals

import click
import os
import shutil

from compose.cli.docker_client import docker_client

from bag8.common import DOMAIN_SUFFIX
from bag8.common import PREFIX
from bag8.common import TMPFOLDER

from bag8.common import call
from bag8.common import simple_name
from bag8.common import get_available_projects
from bag8.common import get_container_name
from bag8.common import get_bag8_path
from bag8.common import get_site_projects
from bag8.common import inspect
from bag8.common import iter_containers
from bag8.common import json_check
from bag8.common import render_yml
from bag8.common import update_resolve_conf


class Tools(object):

    def __init__(self, project=None):
        self.project = project

    def hosts(self):

        running_containers = [c['Names'][0][1:]
                              for c in docker_client().containers(all=True)]

        # dns running or run it ?
        if 'dnsdock' not in running_containers:
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
        # restart
        elif not inspect('dnsdock')[0]['State']['Running']:
            call(' '.join([
                'docker',
                'start',
                'dnsdock',
            ]))

        # update resolve config
        update_resolve_conf()

        # notice
        click.echo('')
        click.echo('Please update your /etc/default/docker with:')
        click.echo('DOCKER_OPTS="-bip 172.17.42.1/24 -dns 172.17.42.1 <your opts>')
        click.echo('')
        click.echo('Have Fun!')

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
