from __future__ import absolute_import, print_function, unicode_literals

import click
import os
import shutil

from compose.cli.docker_client import docker_client

from bag8.common import PREFIX
from bag8.common import TMPFOLDER

from bag8.common import call
from bag8.common import simple_name
from bag8.common import get_available_projects
from bag8.common import get_container_name
from bag8.common import get_bag8_path
from bag8.common import get_site_projects
from bag8.common import iter_containers
from bag8.common import json_check
from bag8.common import render_yml
from bag8.common import update_container_hosts
from bag8.common import update_local_hosts


class Tools(object):

    def __init__(self, project=None, develop_mode=False):
        self.project = project
        self.develop_mode = develop_mode

    def hosts(self):
        """Updates your containers /etc/hosts and/or you local /etc/hosts.
        """
        hosts_list = []
        user_dict = {}

        # get the current list [(ip, domain)]
        client = docker_client()
        for name, container in iter_containers(client=client):
            infos = client.inspect_container(container['Id'])
            ip = infos['NetworkSettings']['IPAddress']
            hostname = infos['Config']['Domainname']
            user = infos['Config']['User'] or 'root'
            if not hostname:
                continue
            hosts_list.append((ip, hostname))
            user_dict[name] = user

        # here s the current hosts
        click.echo('hosts found:')
        click.echo('----')
        click.echo('\n'.join(['{0}\t{1}'.format(*h) for h in hosts_list]))
        click.echo('')

        # update containers ?
        click.echo("Update your containers /etc/hosts ?")
        char = None
        while char not in ['y', 'n']:
            click.echo('Yes (y) or skip (n) ?')
            char = click.getchar()
        if char == 'y':
            for name, __ in iter_containers(client=client):
                update_container_hosts(hosts_list, name,
                                       user_dict.get(name, 'root'))

        # update local ?
        click.echo("Update your local /etc/hosts ?")
        char = None
        while char not in ['y', 'n']:
            click.echo('Yes (y) or no (n) ?')
            char = click.getchar()
        if char == 'y':
            update_local_hosts(hosts_list)

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

        volumes_from = []

        for project in get_site_projects(running=True):
            # shortcut
            name = simple_name(project)
            container_name = containers[name]
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
               prefix):

        environment, links, volumes = json_check(environment, links, volumes)

        render_yml(self.project, environment=environment, links=links,
                   ports=ports, user=user, volumes=volumes,
                   no_volumes=no_volumes, prefix=prefix,
                   develop_mode=self.develop_mode)
