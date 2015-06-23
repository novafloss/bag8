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
DOCKER_IP = config.get('docker_ip', '172.17.42.1')
DATA_PATHS = [
    '.'  # current dir before all
] + config.get('data_paths', [])

RE_WORD = re.compile('\W')


def call(cmd):
    click.echo(cmd)
    subprocess.call(cmd.split())


def confirm(msg):
    click.echo('')
    click.echo(msg)
    click.echo('proceed ?')
    char = None
    while char not in ['y', 'n']:
        click.echo('Yes (y) or no (n) ?')
        char = click.getchar()
    # Yes
    if char == 'y':
        return True


def exec_(cmd):
    click.echo(cmd)
    args_ = cmd.split()
    path = find_executable(args_[0])
    # byebye!
    os.execv(path, args_)


def write_conf(path, content, bak_path=None):

    # keep
    if bak_path:
        call('cp {0} {1}'.format(path, bak_path))

    cmd = [
        'sudo',
        '--reset-timestamp',
        'tee',
        path,
    ]

    # confirm
    if not confirm('`{0}` ?'.format(' '.join(cmd))):
        return

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE)
    process.stdin.write(content)
    process.stdin.close()
    exit_code = process.wait()
    if exit_code != 0:
        raise Exception('Failed to update {0}'.format(path))


def simple_name(text):
    return RE_WORD.sub('', text)


def get_available_projects():
    return [p for __, p in iter_bag8_paths()]


def get_container_name(project, prefix=PREFIX, exit=True):

    containers = [n for n, c in iter_containers(all=True, prefix=prefix,
                                                project=project)]

    if not containers:
        click.echo('no container found for: {0}'.format(project))
        return None if not exit else sys.exit(1)

    if len(containers) > 1:
        click.echo('more than one containers found: {0}'.format(' '.join(containers)))  # noqa
        return None if not exit else sys.exit(1)

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
        # shortcuts
        name = k if k != 'app' else simple_name(project)
        domainname = v.get('domainname', '{0}.{1}'.format(name, DOMAIN_SUFFIX))
        dnsdock_alias = 'DNSDOCK_ALIAS={0}'.format(domainname)
        if dnsdock_alias not in v.get('environment', []):
            if 'environment' not in v:
                v['environment'] = []
            v['environment'].append(dnsdock_alias)
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


def inspect(container, client=None):
    client = client or docker_client()
    return client.inspect_container(container)


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


def update_resolve_conf():

    r_conf_path = '/etc/resolvconf/resolv.conf.d/head'
    r_conf_entry = 'nameserver\t{0}'.format(DOCKER_IP)

    # check already set
    with open(r_conf_path) as f:
        if [l for l in f.readlines() if DOCKER_IP in l.strip()]:
            return

    # here s the current entry
    click.echo('# updates {0} with:'.format(r_conf_path))
    click.echo(r_conf_entry)
    # update head file ?
    click.echo('')
    click.echo('proceed ?')
    char = None
    while char not in ['y', 'n']:
        click.echo('Yes (y) or no (n) ?')
        char = click.getchar()
    # quit
    if char == 'n':
        return

    click.echo('cp {0} /tmp/resolv.conf.d_head.orig')
    subprocess.call(['cp', r_conf_path, '/tmp/resolv.conf.d_head.orig'])

    cmd = [
        'sudo',
        '--reset-timestamp',
        'tee',
        r_conf_path,
    ]
    click.echo(' '.join(cmd))
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE)
    process.stdin.write(r_conf_entry)
    process.stdin.write('\n')
    process.stdin.close()
    exit_code = process.wait()

    if exit_code != 0:
        raise Exception("Failed to update resolvconf")

    cmd = [
        'sudo',
        'resolvconf',
        '-u',
    ]
    click.echo(' '.join(cmd))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    exit_code = process.wait()
    if exit_code != 0:
        raise Exception("Failed to update resolvconf")


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
