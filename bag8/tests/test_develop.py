from __future__ import absolute_import, division, print_function, unicode_literals  # noqa

import pytest

from bag8.tests.base import call


@pytest.mark.needdocker()
def test_develop(local_path, slave_id):

    # new instance
    proc = call(['bag8', 'develop', 'busybox', '-c', 'echo "first run"',
                 '-p', slave_id])
    out, err = proc.communicate()
    assert proc.returncode == 0, err
    assert out.strip() == """
no container found for: busybox
Spawning new instance in background
busybox.yml was generated here: {local_path}/{prefix}_busybox.yml
docker-compose -f {local_path}/{prefix}_busybox.yml -p {prefix} up\
 --allow-insecure-ssl --no-recreate -d
docker exec {prefix}_busybox_1 echo "first run"
"first run"
""".strip().format(**{
        'local_path': local_path,
        'prefix': slave_id,
    })
    assert err.strip() == """
Creating {prefix}_link_1...
Creating {prefix}_busybox_1...
""".strip().format(**{
        'prefix': slave_id,
    })

    # re-enter
    proc = call(['bag8', 'develop', 'busybox', '-c', 'echo "second run"',
                 '-p', slave_id])
    out, err = proc.communicate()
    assert proc.returncode == 0, err
    assert out.strip() == """
docker exec {prefix}_busybox_1 echo "second run"
"second run"
""".strip().format(**{
        'prefix': slave_id,
    })
    assert err.strip() == ''

    # stop
    proc = call(['bag8', 'stop', 'busybox', '-p', slave_id])
    out, err = proc.communicate()
    assert proc.returncode == 0, err
    assert out.strip() == """
docker stop {prefix}_link_1
{prefix}_link_1
docker stop {prefix}_busybox_1
{prefix}_busybox_1
""".strip().format(**{
        'prefix': slave_id,
    })
    assert err.strip() == ''

    # re-start
    proc = call(['bag8', 'develop', 'busybox', '-c', 'echo "third run"',
                 '-p', slave_id])
    out, err = proc.communicate()
    assert proc.returncode == 0, err
    assert out.strip() == """
Restarting instance
docker start {prefix}_link_1
{prefix}_link_1
docker start {prefix}_busybox_1
{prefix}_busybox_1
docker exec {prefix}_busybox_1 echo "third run"
"third run"
""".strip().format(**{
        'prefix': slave_id,
    })
    assert err.strip() == ''
