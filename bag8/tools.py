from __future__ import absolute_import, print_function

import logging
import os
import shutil

from docker.errors import APIError

from bag8.config import Config
from bag8.project import Project
from bag8.utils import check_call
from bag8.utils import inspect


log = logging.getLogger(__name__)


class Tools(object):

    def __init__(self, project=None):
        self.project = project

    def dns(self):

        config = Config()

        # not running
        try:
            if not inspect('dnsdock')['State']['Running']:
                return check_call(['docker', 'start', 'dnsdock'])
        # not exist
        except APIError:
            log.info("Starting docker DNS server.")
            return check_call([
                'docker',
                'run',
                '-d',
                '-v', '/var/run/docker.sock:/var/run/docker.sock',
                '--name', 'dnsdock',
                '-p', '172.17.42.1:53:53/udp',
                config.dnsdock_image,
                "-domain={0}".format(config.domain_suffix)
            ])

    def nginx(self, no_ports=False):

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
            # get container
            container_name = project.get_container_name()
            if not container_name:
                continue
            # update alias
            dnsdock_alias.append('{0}.nginx.{1}'.format(name,
                                                        config.domain_suffix))
            # updates volumes from to share between site and nginx containers
            volumes_from.append(container_name)
            # add link to nginx
            links.append('{0}:{1}.{2}'.format(container_name, name,
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
            '--hostname', 'www.nginx.{0}'.format(config.domain_suffix),
        ]
        if not no_ports:
            args += [
                '-p', '0.0.0.0:80:80',
                '-p', '0.0.0.0:443:443',
            ]
        args = sum([['--volumes-from', v] for v in volumes_from], args)
        args = sum([['-v', v] for v in volumes], args)
        args = sum([['--link', l] for l in links], args)
        args += [
            'nginx',
        ]
        return check_call([str(a) for a in args])
