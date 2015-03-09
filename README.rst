Bag8
====

Let's explain how to orchestrate docker images and containers the easy way.

Installation
------------

.. code:: console

    @me ~$ pip install bag8

The config file
---------------

Bag8 generate temporary files in `~/.config`. You can override some values
by adding a `bag8.yml` file there:

.. code:: yaml

    account: <your account name, ex: bag8>
    registry: <your registry host or None for the docker public one>
    data_paths:
      - <path to your data trees, note: the current dir override all>

The data tree
-------------

In bag8 project we illustrate a simple project tree:

.. code:: console

    @me ~$ tree bag8/busybox
    bag8/busybox/
    ├── Dockerfile
    └── fig.yml
    0 directories, 2 files

Each project should contain a Dockerfile for the build actions, and a fig.yml
file for the orchestration.

My first build
--------------

.. code:: console

    @me ~$ bag8 build -f -t 0.1 busybox
    @me ~$ docker images
    REPOSITORY    TAG  IMAGE ID
    bag8/busybox  0.1  59e5138d13f3

Push it
-------

.. code:: console

    @me ~$ bag8 push -t 0.1 busybox

Let's up
--------

We just add shortcuts to docker-compose cli, then you should run you containers
like that:

.. code:: console

    @me ~$ bag8 up busybox
    @me ~$ bag8 run busybox -c sh
    @me ~$ bag8 exec -i busybox
