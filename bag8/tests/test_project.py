from __future__ import absolute_import, division, print_function, unicode_literals  # noqa

from mock import patch

import pytest

from bag8.project import Project


@pytest.mark.needdocker()
def test_rmi():

    project = Project('busybox')

    # before check
    assert len(project.client.images('bag8/busybox')) == 1

    # remove image
    project.rmi()
    assert len(project.client.images('bag8/busybox')) == 0


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
