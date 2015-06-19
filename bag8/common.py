from __future__ import absolute_import, print_function, unicode_literals

import click
import json
import os
import re
import subprocess
import sys
import yaml
from distutils.spawn import find_executable

from compose.cli.docker_client import docker_client


HERE = os.path.dirname(os.path.abspath(__file__))

# used in projects site.conf files and hosts command
TMPFOLDER = os.path.expanduser('~/.local/bag8/')

# load config
CONFIG_PATH = os.path.expanduser('~/.config/bag8.yml')
if os.path.exists(CONFIG_PATH):
    config = yaml.load(open(CONFIG_PATH))
else:
    click.echo('No config found at `{0}`. Loads default values.'.format(CONFIG_PATH))  # noqa
    config = {}
ACCOUNT = config.get('account', None)
DOMAIN_SUFFIX = config.get('domain_suffix', 'local')
PREFIX = config.get('prefix', 'bag8')
REGISTRY = config.get('registry', None)
DATA_PATHS = [
    '.'  # current dir before all
] + config.get('data_paths', [])

RE_WORD = re.compile('\W')


def call(cmd):
    click.echo(cmd)
    subprocess.call(cmd.split())


def exec_(cmd):
    click.echo(cmd)
    args_ = cmd.split()
    path = find_executable(args_[0])
    # byebye!
    os.execv(path, args_)


def simple_name(text):
    return RE_WORD.sub('', text)


def get_available_projects():
    return [p for __, p in iter_bag8_paths()]


def get_container_name(project, prefix=PREFIX):

    containers = [n for n, c in iter_containers(all=True, prefix=prefix,
                                                project=project)]

    if not containers:
        click.echo('no container found for: {0}'.format(project))
        sys.exit(1)

    if len(containers) > 1:
        click.echo('more than one containers found: {0}'.format(' '.join(containers)))  # noqa
        sys.exit(1)

    return containers[0]


def get_customized_yml(project, ports=True, no_volumes=False,
                       develop=False):
    """Prefixes project sections with project name, ex: pg > busyboxpg.
    """

    yml_path = os.path.join(get_bag8_path(project), 'fig.yml')
    custom_yml = {}

    if not os.path.exists(yml_path):
        click.echo('fig.yml not found: {0}'.format(yml_path))
        return custom_yml

    for k, v in yaml.load(open(yml_path)).items():
        if 'dev_environment' in v and develop and k == 'app':
            # ensure key
            if 'environment' not in v:
                v['environment'] = []
            v['environment'].extend(v.get('dev_environment', []))
        # clean dev section
        if 'dev_environment' in v:
            del v['dev_environment']
        # only for the working app
        if 'dev_volumes' in v and develop and k == 'app':
            # ensure key
            if 'volumes' not in v:
                v['volumes'] = []
            for l in v.get('dev_volumes', []):
                v['volumes'].append(l % os.environ)
        # clean dev volumes
        if 'dev_volumes' in v:
            del v['dev_volumes']
        # remove ports if has one but is not expected
        if 'ports' in v and not ports:
            del v['ports']
        if 'volumes' in v and no_volumes:
            del v['volumes']
        # update sections
        custom_yml[k if k != 'app' else simple_name(project)] = v

    return custom_yml


def get_dockerfile_path(project):
    for path, _project in iter_dockerfiles_paths():
        if _project == project:
            return os.path.join(path, _project)
    click.echo('Dockerfile not found: {0}'.format(path))
    sys.exit(1)


def get_bag8_path(project, exit=True):
    for path, _project in iter_bag8_paths():
        if _project == project:
            return os.path.join(path, _project)
    if exit:
        click.echo('fig.yml not found: {0}'.format(project))
        sys.exit(1)


def get_image_name(project, tag='latest'):
    if REGISTRY and ACCOUNT:
        return '{0}/{1}/{2}:{3}'.format(REGISTRY, ACCOUNT, project, tag)
    if ACCOUNT:
        return '{0}/{1}:{2}'.format(ACCOUNT, project, tag)
    return '{0}:{1}'.format(project, tag)


def get_site_projects(running=False, prefix=PREFIX):

    # list running containers if looking for running ones
    containers = None if not running \
        else {n.split('_')[1]: n for n, __ in iter_containers(prefix=prefix)}

    for project in get_available_projects():
        # shortcut
        name = simple_name(project)
        # not running
        if running and name not in containers:
            continue
        # not a site
        site_path = os.path.join(get_bag8_path(project), 'site.conf')
        if not os.path.exists(site_path):
            continue
        # found one
        yield project


def get_temp_path(project, prefix=PREFIX):

    if not os.path.exists(TMPFOLDER):
        os.makedirs(TMPFOLDER)

    return os.path.join(TMPFOLDER, '{0}_{1}.yml'.format(prefix, project))


def is_valid_project(project):
    return project in get_available_projects()


def iter_containers(all=False, client=None, prefix=PREFIX, project=''):

    client = client or docker_client()
    project = simple_name(project)

    re_service = re.compile('^/{0}_{1}_\d$'.format(prefix, project or '\w*'))
    re_run = re.compile('^/{0}_{1}_run_\d$'.format(prefix, project or '\w*'))

    for c in client.containers(all=all):
        name = [n for n in c['Names'] if re_service.findall(n) or re_run.findall(n)]  # noqa
        # not match
        if not name:
            continue
        # name is something like ['/bag8_busybox_1']
        yield name[0][1:], c


def iter_deps(project):

    yml_path = os.path.join(get_bag8_path(project), 'fig.yml')
    project_yml = yaml.load(open(yml_path))

    internal_links = [s for s in project_yml.keys() if s != 'app']

    for item in project_yml['app'].get('links', []):
        link = item.split(':')[0]
        if link in internal_links:
            continue
        yield link


def iter_dockerfiles_paths():
    for p in DATA_PATHS:
        for d in os.listdir(p):
            if not os.path.exists(os.path.join(p, d, 'Dockerfile')):
                continue
            yield p, d


def iter_bag8_paths():
    for p in DATA_PATHS:
        for d in os.listdir(p):
            if not os.path.exists(os.path.join(p, d, 'fig.yml')):
                continue
            yield p, d


def json_check(environment, links, volumes):

    # environment check
    try:
        environment = [] if not environment else json.loads(environment)
    except Exception:
        click.echo('invalid environment context: {0}'.format(environment))
        sys.exit(1)

    # links check
    try:
        links = [] if not links else json.loads(links)
    except Exception:
        click.echo('invalid links context: {0}'.format(links))
        sys.exit(1)

    # volumes check
    try:
        volumes = [] if not volumes else json.loads(volumes)
    except Exception:
        click.echo('invalid volumes context: {0}'.format(volumes))
        sys.exit(1)

    return environment, links, volumes


def render_yml(project, environment=None, links=None, ports=True, user=None,
               volumes=None, no_volumes=False, prefix=PREFIX,
               develop=False):

    environment = environment if isinstance(environment, list) else []
    links = links if isinstance(links, list) else []
    volumes = volumes if not no_volumes and isinstance(volumes, list) else []

    yml_dict = update_yml_dict({}, project, ports=ports, no_volumes=no_volumes,
                               develop=develop)

    # ensure good app name
    app = simple_name(project)
    app_section = yml_dict[app]

    # updates environment vars
    app_section['environment'] = \
        app_section.get('environment', []) \
        + environment

    # updates links
    app_section['links'] = yml_dict[app].get('links', []) \
        + links

    # clean links according tree permitted names and project accepted ones,
    # ex.: dummy.js:dummyjs.local > dummyjs:dummyjs.local
    app_section['links'] = [':'.join((simple_name(k), v))
                            for k, v in [l.split(':')
                                         for l in app_section['links']]]

    # updates volumes
    app_section['volumes'] = yml_dict[app].get('volumes', []) \
        + volumes

    # set user if not has one
    if user and 'user' not in app_section:
        app_section['user'] = user

    temp_path = get_temp_path(project, prefix)
    with open(temp_path, 'wb') as out_yml:
        # rewrite
        out_yml.write(yaml.safe_dump(yml_dict))

    click.echo('{0}.yml was generated here: {1}'.format(project, temp_path))


HOSTS_HEAD = '# -- bag8 hosts'
HOSTS_FOOT = '# bag8 hosts --'


def _clean_hosts_content(hosts_list, content):
    skip = False
    hosts_to_keep = []
    for l in content.strip().split('\n'):
        l = l.strip()
        # skip line like 'x.x.x.x    pg.local'
        if [h for i, h in hosts_list if l.endswith(h)]:
            continue
        # start skip
        if l == HOSTS_HEAD:
            skip = True
        # keep
        if not skip:
            hosts_to_keep.append(l)
        # stop skip
        if l == HOSTS_FOOT:
            skip = False
    return hosts_to_keep


def _new_hosts_content(hosts_list, hosts_to_keep):
    return '\n'.join([
        '\n'.join(hosts_to_keep),
        HOSTS_HEAD,
        '\n'.join(['{0}\t{1}'.format(*h) for h in hosts_list]),
        HOSTS_FOOT,
        '',
    ])


def update_container_hosts(hosts_list, container, user):

    cmd = 'docker exec -i {0}'.format(container)
    args = ['cat', '/etc/hosts']
    click.echo(' '.join(cmd.split(' ') + args))

    hosts_content = subprocess.check_output(cmd.split(' ') + args)
    hosts_to_keep = _clean_hosts_content(hosts_list, hosts_content)
    new_content = _new_hosts_content(hosts_list, hosts_to_keep)

    args = [] if user == 'root' else [
        'sudo',
    ]
    args += [
        'tee',
        '/etc/hosts',
    ]

    cmd = cmd.split() + args
    click.echo(' '.join(cmd))
    process = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    process.stdin.write(new_content)
    process.stdin.close()
    exit_code = process.wait()

    if exit_code != 0:
        raise Exception("Failed to update container hosts")


def update_local_hosts(hosts_list):
    # filter
    with open('/etc/hosts') as f:
        hosts_to_keep = _clean_hosts_content(hosts_list, f.read())

    for idx, ip_domain in enumerate(hosts_list):
        ip, domain = ip_domain
        if domain != 'nginx.local':
            continue
        # get 'real' domains for nginx
        domain = ' '.join(['{0}.{1}'.format(simple_name(p), DOMAIN_SUFFIX)
                          for p in get_site_projects(running=True)])
        # replace nginx.local with 'real' values
        hosts_list[idx] = (ip, domain)

    new_content = _new_hosts_content(hosts_list, hosts_to_keep)

    click.echo('cp /etc/hosts /tmp/hosts.orig')
    subprocess.call(['cp', '/etc/hosts', '/tmp/hosts.orig'])

    cmd = [
        'sudo',
        '--reset-timestamp',
        'tee',
        '/etc/hosts',
    ]
    click.echo(' '.join(cmd))
    process = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    process.stdin.write(new_content)
    process.stdin.close()
    exit_code = process.wait()

    if exit_code != 0:
        raise Exception("Failed to update local hosts")


def update_yml_dict(yml_dict, project, ports=True, no_volumes=False,
                    develop=False):

    for d in iter_deps(project):
        yml_dict = update_yml_dict(yml_dict, d, ports=ports,
                                   no_volumes=no_volumes,
                                   develop=develop)

    yml_dict.update(get_customized_yml(project, ports=ports,
                                       no_volumes=no_volumes,
                                       develop=develop))

    return yml_dict


class Bag8Mixin(object):

    def __init__(self, container=None, prefix=PREFIX, project=None):
        self._container = container
        self.prefix = prefix
        self.project = project

    def get_containers(self):
        return [n for n, c in iter_containers(all=True, prefix=self.prefix,
                                              project=self.project)]

    @property
    def container(self):
        return self._container or get_container_name(self.project,
                                                     prefix=self.prefix)
