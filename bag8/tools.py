from __future__ import absolute_import, print_function, unicode_literals

import click
import os
import re
import shutil

from time import sleep

from docker.errors import APIError

from bag8.config import Config
from bag8.project import Project
from bag8.utils import check_call
from bag8.utils import confirm
from bag8.utils import inspect
from bag8.utils import write_conf


class Tools(object):

    def __init__(self, project=None):
        self.project = project

    def update_docker_conf(self):

        conf_path = '/etc/default/docker'
        conf_entry = '-bip 172.17.42.1/24 -dns 172.17.42.1'
        conf_content = []

        # check already set
        with open(conf_path) as f:
            conf_content += [l.strip() for l in f.readlines()]

        # update content
        opts = [conf_entry]
        for i, l in enumerate(conf_content):
            if not l.startswith('DOCKER_OPTS='):
                continue
            # has values we don't want to rewrite
            if '-bip' in l or '-dns' in l:
                return
            # keep opts
            opts.append(re.findall('^DOCKER_OPTS="(.*)"', l)[0])
            # remove opts line
            conf_content.remove(l)
        # add new opts
        conf_content.append('DOCKER_OPTS="{0}"'.format(' '.join(opts)))

        click.echo("""
# updates {0} with:
{1}
""".format(conf_path, conf_entry).strip())

        # update resolve config
        write_conf(conf_path, '\n'.join(conf_content) + '\n',
                   bak_path='/tmp/default.docker.orig')

        if confirm('`sudo service docker restart` ?'):
            check_call(['sudo', 'service', 'docker', 'restart'])
            sleep(5)

    def update_dnsmasq_conf(self):

        config = Config()

        conf_path = '/etc/dnsmasq.d/50-bag8'
        if os.path.exists(conf_path):
            return

        conf_content = """
except-interface={0}
bind-interfaces
server=/{1}/{2}
""".format(config.docker_interface, config.domain_suffix,
           config.docker_ip).strip()

        click.echo("""
# updates {0} with:
{1}
""".format(conf_path, conf_content).strip())

        # update dnsmasq config
        write_conf(conf_path, conf_content + '\n')

        if confirm('`sudo service dnsmasq restart` ?'):
            check_call(['sudo', 'service', 'dnsmasq', 'restart'])
            sleep(5)

    def dns(self):

        config = Config()

        # not running
        try:
            if not inspect('dnsdock')['State']['Running']:
                return check_call(['docker', 'start', 'dnsdock'])
        # not exist
        except APIError:
            return check_call([
                'docker',
                'run',
                '-d',
                '-v', '/var/run/docker.sock:/var/run/docker.sock',
                '--name', 'dnsdock',
                '-p', '172.17.42.1:53:53/udp',
                'tonistiigi/dnsdock',
                "-domain={0}".format(config.domain_suffix)
            ])

    def nginx(self):

        config = Config()

        conf_path = os.path.join(config.tmpfolder, 'nginx', 'conf.d')
        # remove previous configs
        shutil.rmtree(conf_path, ignore_errors=True)
        # create new conf folder
        os.makedirs(conf_path)

        log_path = os.path.join(config.tmpfolder, 'nginx', 'log')
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        links = []
        volumes = [
            '{0}:/etc/nginx/conf.d'.format(conf_path),
            '{0}:/var/log/nginx'.format(log_path),
        ]

        dnsdock_alias = []
        volumes_from = []

        for project in Project.iter_projects():
            # shortcut
            name = project.simple_name
            site_conf_path = project.site_conf_path
            if not site_conf_path:
                continue
            # update alias
            dnsdock_alias.append('{0}.nginx.{1}'.format(name,
                                                        config.domain_suffix))
            # get container
            container = project.containers([name])[0]
            # updates volumes from to share between site and nginx containers
            volumes_from.append(container.name)
            # add link to nginx
            links.append('{0}:{1}.{2}'.format(container.name, name,
                                              config.domain_suffix))
            # copy nginx site conf
            shutil.copy(site_conf_path,
                        os.path.join(conf_path, '{0}.conf'.format(name)))

        args = [
            'docker',
            'run',
            '-d',
            '-e', 'DNSDOCK_ALIAS={0}'.format(','.join(dnsdock_alias)),
            '--name', 'nginx',
            '-p', '0.0.0.0:80:80',
            '-p', '0.0.0.0:443:443',
            '--hostname', 'www.nginx.{0}'.format(config.domain_suffix),
        ]
        args = sum([['--volumes-from', v] for v in volumes_from], args)
        args = sum([['-v', v] for v in volumes], args)
        args = sum([['--link', l] for l in links], args)
        args += [
            'nginx',
        ]
        return check_call(args)
