from __future__ import absolute_import, print_function, unicode_literals

import os.path
import logging
from subprocess import check_call

import click

from bag8.common import PREFIX
from bag8.docker import Dockext
from bag8.compose import Figext
from bag8.tools import Tools
from compose.cli.main import setup_logging


def cwdname():
    return os.path.basename(os.getcwd())


@click.group()
def bag8():
    setup_logging()


@click.command()
@click.argument('project')
@click.option('-f', '--force', default=False, is_flag=True,
              help="Force no cache, default: False.")
@click.option('-t', '--tag', default='latest',
              help='Specifies the image tag to build, default: latest')
def build(force, project, tag):
    """Build an image for the current repository and passed tag (or latest),

    eq: docker build --rm (--no-cache) -t <registry>/<account>/<project>:<tag> <Dockerfile>  # noqa
    """
    Dockext(project=project, tag=tag).build(force=force)

bag8.add_command(build)


@click.command()
@click.argument('project')
@click.argument('container', default='')
@click.option('-t', '--tag', default='latest',
              help='Specifies the image tag to build, default: latest')
def commit(container, project, tag):
    """Commits a container for the current repository and passed tag
    (or latest),

    eq: docker commit <container> <registry>/<account>/<project>:<tag>
    """
    Dockext(container=container, project=project, tag=tag).commit()

bag8.add_command(commit)


@click.command()
@click.argument('project')
@click.argument('container', default='')
@click.option('-d', '--dest', default='.',
              help='Dest path when you use the `cp` command, default: `.`.')
@click.option('-s', '--src', help='Source path when you use the `cp` command.')
def cp(container, dest, project, src):
    """Copies a container source path to a local dest path.

    eq: docker cp <container>:<src> <dest>
    """
    Dockext(container=container, project=project).cp(src, dest=dest)

bag8.add_command(cp)


@click.command(name='exec')
@click.argument('project')
@click.argument('container', default='')
@click.option('-c', '--command', default='bash',
              help='Command to exec in a running container, default: `bash`.')
@click.option('-i', '--interactive', default=False, is_flag=True,
              help="Exec command in interactive mode, default: False.")
@click.option('-p', '--prefix', default=PREFIX,
              help="Prefix name of containers.")
def exec_(container, command, interactive, prefix, project):
    """Exec a command into a running container, default: `bash`.

    eq: docker exec (-it) <container> <command>
    """
    Dockext(container=container, prefix=prefix, project=project)\
        .exec_(command=command, interactive=interactive)

bag8.add_command(exec_)


@click.command()
def hosts():
    """Updates /etc/hosts for containers and host

    $ bag8 hosts
    """
    Tools().hosts()

bag8.add_command(hosts)


@click.command()
@click.argument('project')
@click.argument('container', default='')
@click.option('-p', '--prefix', default=PREFIX,
              help="Prefix name of containers.")
def inspect(container, prefix, project):
    """Inspects a container for a given project.

    eq: docker inspect <container>
    """
    Dockext(container=container, prefix=prefix, project=project).inspect()

bag8.add_command(inspect)


@click.command()
@click.argument('project')
@click.argument('container', default='')
@click.option('-p', '--prefix', default=PREFIX,
              help="Prefix name of containers.")
def logs(container, prefix, project):
    """Follows a container logs for a given project.

    eq: docker logs -f <container>
    """
    Dockext(container=container, prefix=prefix, project=project).logs()

bag8.add_command(logs)


@click.command()
@click.option('-l', '--links', default='',
              help='Links list to link with the main app container, ex: \'["app:app.local"]\'.')  # noqa
@click.option('-v', '--volumes', default='',
              help='Volumes list to mount into the container, ex: \'["/tmp:/home/src"]\'.')  # noqa
def nginx(links, volumes):
    """Run nginx container linked with all available sites.
    """
    Tools().nginx(links=links, volumes=volumes)

bag8.add_command(nginx)


@click.command()
def projects():
    """Lists available projects."""
    Tools().projects()

bag8.add_command(projects)


@click.command()
@click.argument('project')
@click.option('-r', '--reuseyml', default=False, is_flag=True,
              help="Reuse previous generated fig.yml file, default: False")
@click.option('-t', '--tag', default=None,
              help='Specifies the image tag to pull with docker command explicitly.')  # noqa
def pull(project, reuseyml, tag):
    """Pulls a project image and its dependencies through compose shortcut. If
    you specify the tag opion it only docker pull a specific image which useful
    for base images like debian.

    ex: $ pull busybox
    docker-compose -f /home/florent/.local/bag8/bag8_busybox.yml -p bag8 pull --allow-insecure-ssl  # noqa

    ex: $ pull -t latest busybox
    docker pull bag8/busybox:latest
    """
    if tag:
        Dockext(project=project, tag=tag).pull()
    else:
        Figext(project=project, reuseyml=reuseyml).pull()

bag8.add_command(pull)


@click.command()
@click.argument('project')
@click.option('-t', '--tag', default='latest',
              help='Specifies the image tag to build, default: latest')
def push(project, tag):
    """Push an image to the current repository and passed tag (or latest),
    ex: <registry>/<account>/<project>:<tag>.
    """
    Dockext(project=project, tag=tag).push()

bag8.add_command(push)


@click.command()
@click.argument('project')
@click.option('-t', '--tag', default='latest',
              help='Specifies the image tag to build, default: latest')
def rebuild(project, tag):
    """Rebuild an image from a existing one with the default wait and run CMD.
    """
    Dockext(project=project, tag=tag).rebuild()

bag8.add_command(rebuild)


@click.command()
@click.argument('project', default=cwdname)
@click.option('--develop', default=False, is_flag=True,
              help='Start the containers in develop mode. default: False.')
@click.option('-e', '--environment', default='',
              help='Environment variables to pass to the container, ex: \'["BRANCH=master", "RUN=test"]\'.')  # noqa
@click.option('-l', '--links', default='',
              help='Links list to link with the main app container, ex: \'["app:app.local"]\'.')  # noqa
@click.option('--ports/--no-ports', default=True,
              help="Expose ports or not, default: True")
@click.option('-u', '--user', default=None,
              help='Specifies the user for the app to run, ex: root.')
@click.option('-v', '--volumes', default='',
              help='Volumes list to mount into the container, ex: \'["/tmp:/home/src"]\'.')  # noqa
@click.option('--no-volumes', default=False, is_flag=True,
              help="Skip volumes if not necessary.")
@click.option('-p', '--prefix', default=PREFIX,
              help="Prefix name of containers.")
def render(project, develop, environment, links, ports, user, volumes,
           no_volumes, prefix):
    """Generates a fig.yml file for a given project and overriding ags.
    """
    (
        Tools(project=project, develop_mode=develop)
        .render(environment, links, ports, user, volumes, no_volumes, prefix)
    )

bag8.add_command(render)


@click.command()
@click.argument('project')
@click.option('-a', '--all', default=False, is_flag=True,
              help="Removes all corresponding containers if has more than one.")  # noqa
@click.option('-p', '--prefix', default=PREFIX,
              help="Prefix name of containers.")
@click.argument('container', default='')
def rm(all, container, prefix, project):
    """Removes a container for a given project.

    eq: docker rm -f <container>
    """
    Dockext(container=container, prefix=prefix, project=project).rm(all=all)

bag8.add_command(rm)


@click.command()
@click.argument('project')
@click.option('-t', '--tag', default='latest',
              help='Specifies the image tag to build, default: latest')
def rmi(project, tag):
    """Remove an image for the current repository and passed tag (or latest),

    eq: docker rmi <registry>/<account>/<project>:<tag>
    """
    Dockext(project=project, tag=tag).rmi()

bag8.add_command(rmi)


@click.command()
@click.argument('project')
@click.option('-c', '--command', default='bash',
              help='Specifies the run command, ex.: /bin/bash.')
@click.option('-e', '--environment', default='',
              help='Environment variables to pass to the container, ex: \'["BRANCH=master", "RUN=test"]\'.')  # noqa
@click.option('-l', '--links', default='',
              help='Links list to link with the main app container, ex: \'["app:app.local"]\'.')  # noqa
@click.option('-r', '--reuseyml', default=False, is_flag=True,
              help="Reuse previous generated fig.yml file, default: False")
@click.option('--ports/--no-ports', default=True,
              help="Expose ports or not, default: True")
@click.option('-u', '--user', default=None,
              help='Specifies the user for the app to run, ex: root.')  # noqa
@click.option('-v', '--volumes', default='',
              help='Volumes list to mount into the container, ex: \'["/tmp:/home/src"]\'.')  # noqa
@click.option('--no-volumes', default=False, is_flag=True,
              help="Skip volumes if not necessary.")
@click.option('-p', '--prefix', default=PREFIX,
              help="Prefix name of containers.")
def run(project, command, environment, links, ports, reuseyml, user, volumes,
        no_volumes, prefix):
    """Run a container with compose for a given project and a given command.

    eq: docker-compose -p <path to project fig.yml> run <?command>
    """
    Figext(project, environment=environment, links=links, ports=ports,
           reuseyml=reuseyml, user=user, volumes=volumes,
           no_volumes=no_volumes, prefix=prefix).run(command=command)

bag8.add_command(run)


@click.command()
@click.argument('project')
@click.argument('container', default='')
@click.option('-i', '--interactive', default=False, is_flag=True,
              help="Start exited container in interactive mode, default: False.")  # noqa
@click.option('-p', '--prefix', default=PREFIX,
              help="Prefix name of containers.")
def start(container, interactive, prefix, project):
    """Start a container in interactive mode for a given project.

    eq: docker start (-i) <container>
    """
    Dockext(container=container, prefix=prefix, project=project).start(interactive=interactive)  # noqa

bag8.add_command(start)


@click.command()
@click.argument('project', default=cwdname)
@click.argument('container', default='')
@click.option('-p', '--prefix', default=PREFIX,
              help="Prefix name of containers.")
def stop(container, prefix, project):
    """Stop a container for a given project.

    eq: docker stop <container>
    """
    Dockext(container=container, prefix=prefix, project=project).stop()

bag8.add_command(stop)


@click.command()
@click.argument('project')
@click.option('-d', '--daemon', default=False, is_flag=True,
              help='Start the containers in the background and leave them running, default: False.')  # noqa
@click.option('--develop', default=False, is_flag=True,
              help='Start the containers in develop mode. default: False.')
@click.option('-e', '--environment', default='',
              help='Environment variables to pass to the container, ex: \'["BRANCH=master", "RUN=test"]\'.')  # noqa
@click.option('-l', '--links', default='',
              help='Links list to link with the main app container, ex: \'["app:app.local"]\'.')  # noqa
@click.option('--ports/--no-ports', default=True,
              help="Expose ports or not, default: True")
@click.option('-r', '--reuseyml', default=False, is_flag=True,
              help="Reuse previous generated fig.yml file, default: False")
@click.option('-u', '--user', default=None,
              help='Specifies the user for the app to run, ex: root.')  # noqa
@click.option('-v', '--volumes', default='',
              help='Volumes list to mount into the container, ex: \'["/tmp:/home/src"]\'.')  # noqa
@click.option('--no-volumes', default=False, is_flag=True,
              help="Skip volumes if not necessary.")
@click.option('-p', '--prefix', default=PREFIX,
              help="Prefix name of containers.")
def up(project, daemon, develop, environment, links, ports, prefix, reuseyml,
       user, volumes, no_volumes):
    """Triggers `docker-compose up` command for a given project.

    Environment, links, user, volumes can be overriden and will be embedded in
    the generated fig.yml.
    """
    Figext(project, environment=environment, links=links, ports=ports,
           prefix=prefix, reuseyml=reuseyml, user=user, volumes=volumes,
           no_volumes=no_volumes, develop_mode=develop).up(daemon=daemon)

bag8.add_command(up)


@bag8.command()
@click.argument('project', default=cwdname)
def develop(project):
    """Drop you in develop environment of your project."""
    from bag8.common import get_container_name

    try:
        container = get_container_name(project)
    except SystemExit:
        # get_container_name calls sys.exit...
        logging.info("Spawning new instance in background")
        check_call(['bag8', 'up', '--daemon', '--develop', project])
        container = get_container_name(project)

    container = Dockext(container=container, project=project)
    data = container.inspect_live()
    if not data[0]['State']['Running']:
        logging.info("Restarting instance")
        check_call(['bag8', 'start', project])

    container.exec_(interactive=True)
