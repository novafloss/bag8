from __future__ import absolute_import, print_function

import os.path
import sys
import yaml

import click

from docker.errors import APIError

from bag8.exceptions import NoProjectYaml
from bag8.project import Project
from bag8.tools import Tools
from bag8.utils import check_call
from bag8.utils import exec_
from bag8.utils import inspect
from bag8.utils import simple_name
from bag8.yaml import Yaml

from compose.service import BuildError
from compose.cli.main import setup_logging


def cwdname():
    return os.path.basename(os.getcwd())


def isatty():
    return sys.stdout.isatty()


@click.group()
def bag8():
    setup_logging()


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('--cache/--no-cache', default=True,
              help="Use cache, default: True")
def build(cache, project):
    p = Project(project)
    try:
        p.build(no_cache=not cache)
    except BuildError:
        sys.exit(1)


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('-c', '--command', default='bash',
              help='Command to exec in a running container, default: None.')
@click.option('-i', '--interactive', default=isatty, is_flag=True,
              help="Use tty mode or not, default: isatty ?")
@click.option('-p', '--prefix', default=None,
              help='Project prefix. default: project.name.')
def develop(command, interactive, prefix, project):
    """Drops you in develop environment of your project.
    """
    Tools().dns()

    p = Project(project, develop=True, prefix=prefix)

    try:
        p.get_services()
    except NoProjectYaml:
        click.echo("Unknown bag8 project %s" % (project,), err=True)
        sys.exit(1)

    # running
    if p.get_container_name():
        pass
    # not running
    elif p.get_container_name(stopped=True):
        p.start()
    # not exist
    else:
        p.up(allow_recreate=False)

    p.execute(command=command, interactive=interactive)


@bag8.command()
def dns():
    """Start or restart docker DNS server."""
    result = Tools().dns()
    if not result:
        return

    out, err, returncode = result
    if returncode:
        click.echo(err + '\n' + out, err=True)
        sys.exit(returncode)


@bag8.command(name='exec')
@click.argument('project', default=cwdname)
@click.option('-c', '--command', default=None,
              help='Command to exec in a running container, default: None.')
@click.option('-p', '--prefix', default=None,
              help='Project prefix. default: project.name.')
@click.option('-s', '--service', default=None,
              help='Service container we want exec, default: project.name.')
def execute(command, prefix, project, service):
    """Exec command in a running container for a given project.
    """
    p = Project(project, prefix=prefix)
    p.execute(command=command, service_name=service)


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('--follow/--no-follow', default=None,
              help='Follow the logs, default: depend if running.')
@click.option('-p', '--prefix', default=None,
              help='Project prefix. default: project.name.')
@click.option('-s', '--service', default=None,
              help='Service container we want the log, default: project.name.')
def logs(follow, prefix, project, service):
    """Get logs for a project related container.
    """
    p = Project(project, prefix=prefix)
    s = simple_name(service or project)

    args = ['docker', 'logs']

    # log follow if running or explicit
    c = p.get_container_name(s)
    if c and follow is not False:
        args += ['-f']

    # do logs
    c = p.get_container_name(s, stopped=True)
    if c:
        return exec_(args + [c])

    click.echo('no container for {0}_{1}_x'.format(p.name, s))


@bag8.command()
@click.option('-p', '--local-projects', default=None, multiple=True,
              help='Projects that need specific nginx upstream server domain (default: all), ex: -p busybox -p link etc.')  # noqa
@click.option('--no-ports', default=False, is_flag=True,
              help='Test mode ? no port binding.')
@click.option('--upstream-server-domain', default=None,
              help='Specify nginx upstream server domain to render in config files.')  # noqa
def nginx(local_projects, no_ports, upstream_server_domain):
    """Run nginx container linked with all available sites.
    """
    # stop previous nginx if exist
    try:
        inspect('nginx')
        check_call(['docker', 'rm', '-f', 'nginx'], exit=False)
    except APIError:
        pass
    # start a new one
    out, err, code = Tools().nginx(
        local_projects=local_projects,
        no_ports=no_ports,
        upstream_server_domain=upstream_server_domain
    )


@bag8.command()
@click.argument('project', default=cwdname)
def pull(project):
    """Pulls a project image (and all its dependencies).
    """
    p = Project(project)
    p.pull()


@bag8.command()
@click.argument('project', default=cwdname)
def push(project):
    """Push the image of the given project,
    """
    p = Project(project)
    p.push(service_names=[p.simple_name], insecure_registry=True)


@bag8.command()
@click.argument('project', default=cwdname)
@click.argument('output', type=click.File('wb'), default='fig.yml')
def render(output, project):
    """Renders fig.yml like content to out file, default: fig.yml.
    """
    yaml.safe_dump(Yaml(Project(project)).data, output, indent=2,
                   encoding='utf-8', allow_unicode=True)


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('-p', '--prefix', default=None,
              help='Project prefix. default: project.name.')
@click.option('-s', '--service', default=None,
              help='Service container we want exec, default: project.name.')
def rm(prefix, project, service):
    """Removes containers for a given project.
    """
    p = Project(project, prefix=prefix)
    service_names = None if not service else [service]
    p.stop(service_names=service_names, timeout=0)
    p.remove_stopped(service_names=service_names)


@bag8.command()
@click.argument('project', default=cwdname)
def rmi(project):
    """Removes an image locally.
    """
    Project(project).rmi()


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('-c', '--command', default=None,
              help='Command to run, default: None.')
@click.option('-d', '--develop', default=False, is_flag=True,
              help='Start the containers in develop mode. default: False.')
@click.option('--keep', default=False, is_flag=True,
              help='Do not --rm after, default: False')
@click.option('-p', '--prefix', default=None,
              help='Project prefix. default: project.name.')
def run(command, develop, keep, prefix, project):
    """Start containers for a given project.
    """
    p = Project(project, develop=develop, prefix=prefix)
    p.run(command=command, remove=not keep)


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('-i', '--interactive', default=False, is_flag=True,
              help='Start previous runned/keeped container, default: False.')
@click.option('-p', '--prefix', default=None,
              help='Project prefix. default: project.name.')
@click.option('-s', '--service', default=None,
              help='Service container we want start, default: None.')
def start(interactive, prefix, project, service):
    """Start containers for a given project.
    """
    p = Project(project, prefix=prefix)
    service_names = None if not service else [service]
    p.start(interactive=interactive, service_names=service_names)


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('-p', '--prefix', default=None,
              help='Project prefix. default: project.name.')
@click.option('-s', '--service', default=None,
              help='Service container we want stop, default: None.')
def stop(project, prefix, service):
    """Stop containers for a given project.
    """
    p = Project(project, prefix=prefix)
    service_names = None if not service else [service]
    p.stop(service_names=service_names, timeout=0)


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('-d', '--develop', default=False, is_flag=True,
              help='Start the containers in develop mode. default: False.')
@click.option('-p', '--prefix', default=None,
              help='Project prefix. default: project.name.')
def up(develop, prefix, project):
    """Up containers for a given project
    """
    p = Project(project, develop=develop, prefix=prefix)
    try:
        p.up(allow_recreate=False)
    except BuildError as e:
        click.echo(e.reason, err=True)
        sys.exit(1)
