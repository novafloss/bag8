from __future__ import absolute_import, division, print_function, unicode_literals  # noqa

import os

from bag8.project import Project
from bag8.yaml import Yaml


def test_data():

    # normal
    project = Project('busybox')
    assert Yaml(project).data == {
        'busybox': {
            'dockerfile': os.path.join(project.build_path, 'Dockerfile'),
            'environment': [
                'DNSDOCK_ALIAS=busybox.docker',
                'DNSDOCK_IMAGE=',
                'BAG8_LINKS=link'
            ],
            'image': 'bag8/busybox',
            'links': [
                'link:link'
            ]
        },
        'link': {
            'environment': [
                'DNSDOCK_ALIAS=link.docker',
                'DNSDOCK_IMAGE=',
                'BAG8_LINKS='
            ],
            'image': 'bag8/busybox'
        }
    }

    # develop
    project = Project('busybox', develop=True)
    assert Yaml(project).data == {
        'busybox': {
            'dockerfile': os.path.join(project.build_path, 'Dockerfile'),
            'environment': [
                'DNSDOCK_ALIAS=busybox.docker',
                'DNSDOCK_IMAGE=',
                'BAG8_LINKS=link',
                'DUMMY=yo'
            ],
            'image': 'bag8/busybox',
            'links': [
                'link:link'
            ],
            'volumes': [
                '/tmp:/tmp'
            ]
        },
        'link': {
            'environment': [
                'DNSDOCK_ALIAS=link.docker',
                'DNSDOCK_IMAGE=',
                'BAG8_LINKS='
            ],
            'image': 'bag8/busybox'
        }
    }


def test_service_dicts():

    # normal
    project = Project('busybox')
    assert sorted(Yaml(project).service_dicts) == sorted([
        {
            'name': 'busybox',
            'dockerfile': os.path.join(project.build_path, 'Dockerfile'),
            'environment': [
                'DNSDOCK_ALIAS=busybox.docker',
                'DNSDOCK_IMAGE=',
                'BAG8_LINKS=link'
            ],
            'image': 'bag8/busybox',
            'links': [
                'link:link'
            ]
        },
        {
            'name': 'link',
            'environment': [
                'DNSDOCK_ALIAS=link.docker',
                'DNSDOCK_IMAGE=',
                'BAG8_LINKS='
            ],
            'image': 'bag8/busybox'
        }
    ])

    # develop
    project = Project('busybox', develop=True)
    assert sorted(Yaml(project).service_dicts) == sorted([
        {
            'name': 'busybox',
            'dockerfile': os.path.join(project.build_path, 'Dockerfile'),
            'environment': [
                'DNSDOCK_ALIAS=busybox.docker',
                'DNSDOCK_IMAGE=',
                'BAG8_LINKS=link',
                'DUMMY=yo'
            ],
            'image': 'bag8/busybox',
            'links': [
                'link:link'
            ],
            'volumes': [
                '/tmp:/tmp'
            ]
        },
        {
            'name': 'link',
            'environment': [
                'DNSDOCK_ALIAS=link.docker',
                'DNSDOCK_IMAGE=',
                'BAG8_LINKS='
            ],
            'image': 'bag8/busybox'
        }
    ])
