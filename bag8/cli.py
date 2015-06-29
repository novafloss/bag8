from __future__ import absolute_import, print_function, unicode_literals

import os.path
import sys

from socket import gaierror
from socket import getaddrinfo

import click

from docker.errors import APIError

from bag8.config import Config
from bag8.project import Project
from bag8.tools import Tools
from bag8.utils import check_call
from bag8.utils import inspect

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
    p.build(no_cache=not cache)


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('-c', '--command', default='bash',
              help='Command to exec in a running container, default: None.')
@click.option('-i', '--interactive', default=isatty, is_flag=True,
              help="Use tty mode or not, default: isatty ?")
def develop(command, interactive, project):
    """Drops you in develop environment of your project.
    """
    Tools().dns()

    p = Project(project, develop=True)

    # running
    if p.containers([p.name]):
        pass
    # not running
    if p.containers([p.name], stopped=True):
        p.start()
    # not exist
    else:
        p.up()

    p.execute(command=command, interactive=interactive)


@bag8.command()
def dns():
    """Start or restart docker DNS server."""
    result = Tools().dns()
    if not result:
        return

    out, err, returncode = result
    if returncode:
        click.echo(err + '\n' + out)
        sys.exit(returncode)


@bag8.command(name='exec')
@click.argument('project', default=cwdname)
@click.option('-c', '--command', default=None,
              help='Command to exec in a running container, default: None.')
def execute(command, project):
    """Exec command in a running container for a given project.
    """
    p = Project(project)
    p.execute(command=command)


@bag8.command()
def nginx():
    """Run nginx container linked with all available sites.
    """
    # stop previous nginx if exist
    try:
        inspect('nginx')
        check_call(['docker', 'rm', '-f', 'nginx'], exit=False)
    except APIError:
        pass
    # start a new one
    out, err, code = Tools().nginx()


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
def rm(project):
    """Removes containers for a given project.
    """
    p = Project(project, develop=develop)
    p.stop(timeout=0)
    p.remove_stopped()


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
              help="Do not --rm after, default: False")
def run(command, develop, keep, project):
    """Start containers for a given project.
    """
    p = Project(project, develop=develop)
    p.run(command=command, remove=not keep)


@bag8.command()
def setup():
    """Setup docker and dnsmasq."""

    Tools().update_dnsmasq_conf()
    Tools().update_docker_conf()
    Tools().dns()

    try:
        getaddrinfo('dnsdock.' + Config().domain_suffix, 53)
    except gaierror:
        click.echo("docker DNS resolution fails!")
        sys.exit(1)
    else:
        click.echo("docker DNS resolution is ready.")


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('-i', '--interactive', default=False, is_flag=True,
              help='Start previous runned/keeped container, default: False.')
def start(interactive, project):
    """Start containers for a given project.
    """
    p = Project(project)
    p.start(interactive=interactive)


@bag8.command()
@click.argument('project', default=cwdname)
def stop(project):
    """Stop containers for a given project.
    """
    p = Project(project)
    p.stop(timeout=1)


@bag8.command()
@click.argument('project', default=cwdname)
@click.option('-d', '--develop', default=False, is_flag=True,
              help='Start the containers in develop mode. default: False.')
def up(develop, project):
    """Up containers for a given project
    """
    p = Project(project, develop=develop)
    p.up(allow_recreate=False)
