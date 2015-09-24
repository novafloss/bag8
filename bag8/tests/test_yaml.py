from __future__ import absolute_import, division, print_function

import os

from bag8.project import Project
from bag8.yaml import Yaml


def test_data():

    # normal
    project = Project('busybox')
    assert Yaml(project).data == {
        'busybox': {
            'dockerfile': os.path.join(project.build_path, 'Dockerfile'),
            'environment': {
                'BAG8_LINKS': 'link',
                'DNSDOCK_ALIAS': 'busybox.docker',
                'DNSDOCK_IMAGE': '',
                'DUMMY': 'nothing here',
            },
            'image': 'bag8/busybox',
            'links': [
                'link:link'
            ]
        },
        'link': {
            'environment': {
                'BAG8_LINKS': '',
                'DNSDOCK_ALIAS': 'link.docker',
                'DNSDOCK_IMAGE': '',
            },
            'image': 'bag8/busybox'
        }
    }

    # develop
    project = Project('busybox', develop=True)
    assert Yaml(project).data == {
        'busybox': {
            'dockerfile': os.path.join(project.build_path, 'Dockerfile'),
            'environment': {
                'BAG8_LINKS': 'link',
                'DNSDOCK_ALIAS': 'busybox.docker',
                'DNSDOCK_IMAGE': '',
                'DUMMY': 'yo',
            },
            'image': 'bag8/busybox',
            'links': [
                'link:link'
            ],
            'volumes': [
                '/tmp:/tmp'
            ]
        },
        'link': {
            'environment': {
                'BAG8_LINKS': '',
                'DNSDOCK_ALIAS': 'link.docker',
                'DNSDOCK_IMAGE': '',
            },
            'image': 'bag8/busybox'
        }
    }


def test_service_dicts():

    # normal
    project = Project('busybox')
    assert sorted(Yaml(project).service_dicts) == sorted([
        {
            'name': 'busybox',
            'bag8_name': 'busybox',
            'dockerfile': os.path.join(project.build_path, 'Dockerfile'),
            'environment': {
                'BAG8_LINKS': 'link',
                'DNSDOCK_ALIAS': 'busybox.docker',
                'DNSDOCK_IMAGE': '',
                'DUMMY': 'nothing here',
            },
            'image': 'bag8/busybox',
            'links': [
                'link:link'
            ]
        },
        {
            'name': 'link',
            'bag8_name': 'link',
            'environment': {
                'BAG8_LINKS': '',
                'DNSDOCK_ALIAS': 'link.docker',
                'DNSDOCK_IMAGE': '',
            },
            'image': 'bag8/busybox'
        }
    ])

    # develop
    project = Project('busybox', develop=True)
    assert sorted(Yaml(project).service_dicts) == sorted([
        {
            'name': 'busybox',
            'bag8_name': 'busybox',
            'dockerfile': os.path.join(project.build_path, 'Dockerfile'),
            'environment': {
                'BAG8_LINKS': 'link',
                'DNSDOCK_ALIAS': 'busybox.docker',
                'DNSDOCK_IMAGE': '',
                'DUMMY': 'yo',
            },
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
            'bag8_name': 'link',
            'environment': {
                'BAG8_LINKS': '',
                'DNSDOCK_ALIAS': 'link.docker',
                'DNSDOCK_IMAGE': '',
            },
            'image': 'bag8/busybox'
        }
    ])

    # complex name
    project = Project('link.2')
    assert sorted(Yaml(project).service_dicts) == sorted([
        {
            'name': 'link2',
            'bag8_name': 'link.2',
            'dockerfile': os.path.join(project.build_path, 'Dockerfile'),
            'environment': {
                'BAG8_LINKS': '',
                'DNSDOCK_ALIAS': 'link2.docker',
                'DNSDOCK_IMAGE': '',
            },
            'image': 'bag8/busybox',
            'links': []
        }
    ])
