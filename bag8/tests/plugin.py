from __future__ import absolute_import, division, print_function, unicode_literals  # noqa

import os
import yaml

import pytest

import bag8

from bag8.tests.base import call
from bag8.tools import Tools


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


@pytest.fixture(autouse=True, scope='function')
def _setup(config_path):

    settings = {
        b'account': b'bag8',
        b'data_paths': [
            os.path.join(os.path.dirname(os.path.abspath(bag8.__file__)),
                         '..', 'data'),
        ],
    }
    with open(config_path, 'w') as fo:
        yaml.dump(settings, fo, indent=2, default_flow_style=False, width=80)

    # build needed image
    call(['bag8', 'build', 'busybox'])


def _rm_all(slave_id):
    call(['bag8', 'rm', '-a', 'busybox', '-p', slave_id])
    call(['docker', 'rm', '-f', 'dnsdock'])


@pytest.fixture(scope='function')
def needdocker(request, slave_id):
    # remove containers before tests
    _rm_all(slave_id)

    # run dns for all tests
    Tools().dns()

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
