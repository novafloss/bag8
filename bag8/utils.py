from __future__ import absolute_import, division, print_function


import os
import re
import socket
import sys

from itertools import count
from functools import partial
from subprocess import Popen
from subprocess import PIPE
from time import sleep

import click

from distutils.spawn import find_executable

from compose.cli.docker_client import docker_client

from bag8.exceptions import CheckCallFailed, WaitLinkFailed

RE_WORD = re.compile('\W')


call = partial(Popen, stdout=PIPE, stderr=PIPE)


def check_call(args, exit=True, **kwargs):

    proc = call(args, **kwargs)
    out, err = proc.communicate()

    if not proc.returncode:
        return out, err, proc.returncode

    if exit:
        click.echo(out)
        click.echo(err)
        sys.exit(proc.returncode)

    else:
        raise CheckCallFailed(out + '\n' + err)


def exec_(args):
    # byebye!
    os.execv(find_executable(args[0]), args)


def wait_(host, port, max_retry=10, retry_interval=1):
    counter = count()
    while counter.next() < max_retry:
        try:
            return socket.socket().connect((host, int(port)))
        except socket.error:
            click.echo('wait for {}:{}'.format(host, port))
            sleep(retry_interval)
    raise WaitLinkFailed("can't link to {}:{}".format(host, port))


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


def inspect(container, client=None):
    client = client or docker_client()
    return client.inspect_container(container)


def simple_name(text):
    return RE_WORD.sub('', text)


def write_conf(path, content, bak_path=None):

    # keep
    if bak_path:
        call(['cp', path, bak_path])

    cmd = [
        'sudo',
        '--reset-timestamp',
        'tee',
        path,
    ]

    # confirm
    if not confirm('`{0}` ?'.format(' '.join(cmd))):
        return

    process = call(cmd, stdin=PIPE)
    process.stdin.write(content)
    process.stdin.close()
    exit_code = process.wait()
    if exit_code != 0:
        raise Exception('Failed to update {0}'.format(path))
