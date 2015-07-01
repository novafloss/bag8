from __future__ import absolute_import, division, print_function, unicode_literals  # noqa

import os
import tempfile

from functools import partial

import pytest

from bag8.project import Project
from bag8.utils import check_call as base_check_call
from bag8.utils import inspect


check_call = partial(base_check_call, exit=False)


@pytest.mark.synchronous
@pytest.mark.needdocker()
def test_build(client):

    # rmi first
    Project('busybox').rmi()

    out, err, code = check_call(['bag8', 'build', 'busybox'])
    assert code == 0, err
    assert len(client.images('bag8/busybox')) == 1


@pytest.mark.needdocker()
def test_develop(slave_id):

    # not exist -> create
    out, err, code = check_call(['bag8', 'develop', 'busybox',
                                 '-c', 'echo "hi"', '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert out.strip() == 'hi'

    # check container exist
    p = Project('busybox', develop=True, prefix=slave_id)
    assert len(p.containers(['busybox'])) == 1

    # started -> re-use
    out, err, code = check_call(['bag8', 'develop', 'busybox',
                                 '-c', 'echo "yo"', '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert out.strip() == 'yo'

    # stop
    p.stop(timeout=0)
    assert len(p.containers(['busybox'])) == 0

    # before test
    tmp_file = tempfile.NamedTemporaryFile().name
    if os.path.exists(tmp_file):
        os.remove(tmp_file)

    # not started -> start -> reuse and touch file in shared volume
    out, err, code = check_call(['bag8', 'develop', 'busybox',
                                 '-c', 'touch "{0}"'.format(tmp_file),
                                 '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert os.path.exists(tmp_file)

    out, err, code = check_call(['bag8', 'develop', 'busybox', '-c', 'env',
                                 '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert 'DUMMY=yo' in out.split()


@pytest.mark.needdocker()
def test_develop_no_recreate(slave_id):

    # develop
    check_call(['bag8', 'develop', 'busybox', '-c', 'echo "hi"',
                '-p', slave_id])

    container = '{0}_busybox_1'.format(slave_id)

    # rm
    out, err, code = check_call(['docker', 'rm', '-f', container])
    assert code == 0, err + '\n' + out
    assert out.strip() == container

    # should not recreate container link
    out, err, code = check_call(['bag8', 'develop', 'busybox',
                                 '-c', 'echo "hi"', '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert err.strip() == 'Creating {0}_busybox_1...'.format(slave_id)
    assert out.strip() == 'hi'


@pytest.mark.needdocker()
def test_dns():

    # not exist -> create
    out, err, code = check_call(['bag8', 'dns'])

    assert code == 0, err + '\n' + out
    assert inspect('dnsdock')['State']['Running']


@pytest.mark.needdocker()
def test_execute(slave_id):

    # up a container to execute command in
    check_call(['bag8', 'up', 'busybox', '-p', slave_id])

    # execute something
    out, err, code = check_call(['bag8', 'exec', 'busybox',
                                 '-c', 'echo "hi"', '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert out.strip() == 'hi'

    # execute something in link container
    out, err, code = check_call(['bag8', 'exec', 'busybox', '-s', 'link',
                                 '-c', 'echo "hi link"', '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert out.strip() == 'hi link'


@pytest.mark.needdocker()
def test_logs(slave_id):

    # run some messages
    check_call(['bag8', 'run', 'busybox', '--keep', '-c', 'echo "busybox"',
                '-p', slave_id])

    # logs main
    out, err, code = check_call(['bag8', 'logs', 'busybox', '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert out.strip() == 'busybox'

    # logs service
    out, err, code = check_call(['bag8', 'logs', 'busybox', '-s', 'link',
                                 '--no-follow', '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert out.strip() == ''

    # logs ?
    out, err, code = check_call(['bag8', 'logs', 'busybox', '-s', 'what',
                                 '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert out.strip() == 'no container for {0}_what_x'.format(slave_id)


@pytest.mark.needdocker()
def test_nginx(slave_id):

    # up a container to proxify
    check_call(['bag8', 'up', 'busybox', '-p', slave_id])

    out, err, code = check_call(['bag8', 'nginx'])
    assert code == 0, err + '\n' + out
    assert inspect('nginx')['State']['Running']


@pytest.mark.synchronous
@pytest.mark.needdocker()
def test_pull(client):

    # rmi first
    Project('busybox').rmi()
    assert len(client.images('bag8/busybox')) == 0

    out, err, code = check_call(['bag8', 'pull', 'busybox'])
    assert code == 0, err
    assert len(client.images('bag8/busybox')) == 1


@pytest.mark.needdocker()
def test_push():
    pass  # lets say it works


@pytest.mark.needdocker()
def test_rm(slave_id):

    # up a container to proxify
    check_call(['bag8', 'up', 'busybox', '-p', slave_id])

    # check container exist
    p = Project('busybox', prefix=slave_id)
    assert [c.name for c in p.containers()] == [
        '{0}_busybox_1'.format(p.name),
        '{0}_link_1'.format(p.name),
    ]

    # recursive rm
    check_call(['bag8', 'rm', 'busybox', '-p', slave_id])
    assert len(p.containers(stopped=True)) == 0

    # new up
    check_call(['bag8', 'up', 'busybox', '-p', slave_id])
    assert len(p.containers(stopped=True)) == 2

    # single rm
    check_call(['bag8', 'rm', 'busybox', '-p', slave_id,
                '-s', 'busybox'])
    assert len(p.containers()) == 1
    assert [c.name for c in p.containers()][0] == '{0}_link_1'.format(slave_id)


@pytest.mark.synchronous
@pytest.mark.needdocker()
def test_rmi(client):

    # initial test
    assert len(client.images('bag8/busybox')) == 1

    # rmi first
    Project('busybox').rmi()
    assert len(client.images('bag8/busybox')) == 0


@pytest.mark.needdocker()
def test_run(slave_id):

    # not exist -> create
    out, err, code = check_call(['bag8', 'run', 'busybox',
                                 '-c', 'echo "hi"', '-p', slave_id])
    assert code == 0, err + '\n' + out
    assert out.strip() == 'hi'


@pytest.mark.needdocker()
def test_start(slave_id):

    # up a container to proxify
    check_call(['bag8', 'up', 'busybox', '-p', slave_id])

    # check container exist
    p = Project('busybox', prefix=slave_id)
    assert len(p.containers(['busybox'])) == 1

    # stop all
    check_call(['bag8', 'stop', 'busybox', '-p', slave_id])
    assert [c.name for c in p.containers()] == []

    # start all
    check_call(['bag8', 'start', 'busybox', '-p', slave_id])
    assert [c.name for c in p.containers()] == [
        '{0}_busybox_1'.format(slave_id),
        '{0}_link_1'.format(slave_id),
    ]

    # stop all again
    check_call(['bag8', 'stop', 'busybox', '-p', slave_id])
    assert [c.name for c in p.containers()] == []

    # start one
    check_call(['bag8', 'start', 'busybox', '-p', slave_id,
                '-s', 'link'])
    assert [c.name for c in p.containers()] == [
        '{0}_link_1'.format(slave_id),
    ]


@pytest.mark.needdocker()
def test_stop(slave_id):

    # up a container to proxify
    check_call(['bag8', 'up', 'busybox', '-p', slave_id])

    # check container exist
    p = Project('busybox', prefix=slave_id)
    assert len(p.containers(['busybox'])) == 1

    # stop
    check_call(['bag8', 'stop', 'busybox', '-p', slave_id])
    assert len(p.containers(['busybox'])) == 0
    assert len(p.containers(['busybox'], stopped=True)) == 1

    # start all again
    check_call(['bag8', 'start', 'busybox', '-p', slave_id])
    assert [c.name for c in p.containers()] == [
        '{0}_busybox_1'.format(slave_id),
        '{0}_link_1'.format(slave_id),
    ]

    # stop one
    check_call(['bag8', 'stop', 'busybox', '-p', slave_id,
                '-s', 'busybox'])
    assert [c.name for c in p.containers()] == [
        '{0}_link_1'.format(slave_id),
    ]


@pytest.mark.needdocker()
def test_up(slave_id):

    # up a container to proxify with prefix
    check_call(['bag8', 'up', 'busybox', '-p', slave_id])

    # check container exist
    p = Project('busybox', prefix=slave_id)
    assert len(p.containers(['busybox'])) == 1
