from __future__ import absolute_import, division, print_function

from mock import patch

import pytest

from bag8.project import Project


@pytest.mark.exclusive
@pytest.mark.needdocker()
def test_rmi():

    project = Project('busybox')

    # before check
    assert len(project.client.images('bag8/busybox')) == 1

    # remove image
    project.rmi()
    assert len(project.client.images('bag8/busybox')) == 0


@pytest.mark.exclusive
@pytest.mark.needdocker()
def test_build():

    project = Project('busybox')

    # remove previous image
    project.rmi()
    assert len(project.client.images('bag8/busybox')) == 0

    # rebuild
    project.build()
    assert len(project.client.images('bag8/busybox')) == 1


def test_pull_insecure_registry():

    project = Project('busybox')

    # default behaviour
    with patch('compose.service.Service.pull') as mock:
        project.pull()
    mock.assert_called_with(insecure_registry=False)

    # with insecure_registry context
    project.config.insecure_registry = True

    with patch('compose.service.Service.pull') as mock:
        project.pull()
    mock.assert_called_with(insecure_registry=True)


@pytest.mark.needdocker()
def test_iter_projects(slave_id):

    project = Project('busybox', prefix=slave_id)
    project.up()

    containers = ['{0}:{1}'.format(p.prefix, p.bag8_name)
                  for p in project.iter_projects()]
    assert [c for c in [
        '{0}:busybox'.format(slave_id),
        '{0}:link'.format(slave_id),
    ] if c in containers]

    # up new container with the same prefix
    project = Project('link.2', prefix=slave_id)
    project.up()

    containers = ['{0}:{1}'.format(p.prefix, p.bag8_name)
                  for p in project.iter_projects()]
    assert [c for c in [
        '{0}:link.2'.format(slave_id),
        '{0}:busybox'.format(slave_id),
        '{0}:link'.format(slave_id),
    ] if c in containers]


def test_project_environment():
    project = Project('busybox')
    assert project.environment == {
        'DUMMY': 'nothing here',
        'NGINX_UPSTREAM_SERVER_DOMAIN': 'link.docker'
    }
    project = Project('link')
    assert project.environment == {
        'DUMMY': 'nothing here too'
    }
    project = Project('link.2')
    assert project.environment == {}
