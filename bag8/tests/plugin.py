from __future__ import absolute_import, division, print_function

import os
import yaml

from functools import partial

import pytest

from compose.cli.docker_client import docker_client

import bag8

from bag8.config import Config
from bag8.exceptions import CheckCallFailed
from bag8.utils import check_call as base_check_call


check_call = partial(base_check_call, exit=False)


@pytest.fixture(scope='session')
def client():
    return docker_client()


@pytest.fixture(scope='function')
def slave_id(request):
    slaveinput = getattr(request.config, 'slaveinput', {})
    return slaveinput.get('slaveid', 'default')


@pytest.fixture(scope='function')
def home_path(slave_id):
    home_path = os.path.join('/tmp/bag8_config_{0}'.format(slave_id))
    os.environ['HOME'] = home_path
    return home_path


@pytest.fixture(scope='function')
def config_path(home_path):
    config_dir = os.path.join(home_path, '.config')
    if not os.path.exists(config_dir):
        os.makedirs(os.path.join(home_path, '.config'))
    return os.path.join(config_dir, 'bag8.yml')


@pytest.fixture(scope='function')
def local_path(home_path):
    return os.path.join(home_path, '.local', 'bag8')


@pytest.fixture(scope='function')
def config():
    return Config()


@pytest.fixture(autouse=True, scope='function')
def _setup(config_path, slave_id):

    settings = {
        b'account': b'bag8',
        b'data_paths': [
            os.path.join(os.path.dirname(os.path.abspath(bag8.__file__)),
                         b'..', b'data'),
        ],
        b'prefix': slave_id,
    }
    with open(config_path, 'w') as fo:
        yaml.dump(settings, fo, indent=2, default_flow_style=False, width=80)

    # build needed image
    check_call(['bag8', 'build', 'busybox'])


def _rm_all(slave_id):
    try:
        check_call(['bag8', 'rm', 'busybox', '-p', slave_id])
    except CheckCallFailed:
        pass
    try:
        check_call(['bag8', 'rm', 'link.2', '-p', slave_id])
    except CheckCallFailed:
        pass
    try:
        check_call(['docker', 'rm', 'dnsdock'])
    except CheckCallFailed:
        pass
    try:
        check_call(['docker', 'rm', 'nginx'])
    except CheckCallFailed:
        pass


@pytest.fixture(scope='function')
def needdocker(request, slave_id, _setup):
    # remove containers before tests
    _rm_all(slave_id)

    # run dns for all tests
    from bag8.tools import Tools
    Tools().dns()

    # rebuild busybox
    from bag8.project import Project
    Project('busybox').build

    # remove containers after tests
    def clean():
        _rm_all(slave_id)
    request.addfinalizer(clean)


@pytest.fixture(autouse=True)
def _needdocker_marker(request):
    marker = request.keywords.get('needdocker', None)
    if not marker:
        return
    request.getfuncargvalue('needdocker')
