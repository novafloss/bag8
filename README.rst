Bag8
====

.. image:: https://travis-ci.org/novafloss/bag8.svg
   :target: https://travis-ci.org/novafloss/bag8
   :alt: We are under CI!!

Let's explain how to orchestrate docker images and containers the easy way.

Installation
------------

.. code:: console

    @me ~$ pip install bag8

The config file
---------------

Bag8 read his config from `~/.config`. You can override some values by adding
a `bag8.yml` file there:

.. code:: yaml

    account: <your account name, ex: bag8>
    registry: <your registry host or None for the docker public one>
    data_paths:
      - <path to your data trees, note: the current dir override all>

The data tree
-------------

In ``bag8`` project we illustrate a simple project tree:

.. code:: console

    @me ~$ tree data/
    data/
    ├── busybox
    │   ├── Dockerfile
    │   ├── fig.yml
    │   └── site.conf
    ├── link
    │   ├── Dockerfile
    │   └── fig.yml
    └── link.2
        ├── Dockerfile
        └── fig.yml

.. note:: Each project should contain a Dockerfile for the build actions, and
          a fig.yml file for the orchestration.

.. note:: We use the name of the folders as project names.

The CLI
-------

``Bag8`` commands can be run from anywhere since the ``bag8`` executable is
available in your current path and your config include your project ``data``
dir in the ``data_paths`` list.

Thanks to ``click`` cli framework, ``bag8`` command and subcommands will all
print there documentation with the ``--help`` argument.

My first build
--------------

Here is how we rebuild a ``bag8`` image. You can build it from anywhere since
the ``bag8`` command is available in your current path and your ``bag8.yml``
config include the ``bag8`` project ``data`` dir in the ``data_paths`` list.

.. code:: console

    @me ~$ bag8 build busybox
    @me ~$ docker images
    REPOSITORY    TAG     IMAGE ID
    bag8/busybox  latest  59e5138d13f3

Here is how we can push it to the *bag8* account of the *docker HUB*:

.. code:: console

    @me ~$ bag8 push busybox

You can change ``account`` and ``registry`` value in your config according your
needs, for example:

.. code:: yaml

    account: rd
    registry: hub.mylittlecompany.org

It should build an tag your images as follow to be pushed to your registry:

.. code:: console

    @me ~$ bag8 build busybox
    @me ~$ docker images
    REPOSITORY                          TAG     IMAGE ID
    hub.mylittlecompany.org/rd/busybox  latest  59e5138d13f3

Let's up
--------

In our demo data we have a ``busybox`` project to link with a ``link`` project.
``busybox`` container should wait and ``link`` container listen for some calls
on the 1234 port.

Up
^^

By default if you up the ``busybox`` project it will start a ``link`` container
as ``busybox`` dependency then a ``busybox`` container. When the ``busybox``
container starts, and because ``link`` container expose port 1234, it will
wait that ``link`` container is ready and really listen on 1234.

.. note:: To test port availability we need correct dns setup. See bellow for
          more info about it.

Here is want we should have:

.. code:: console

    @me ~$ bag8 dns # to make sure dnsdock is up
    @me ~$ bag8 up busybox
    Creating busybox_link_1...
    Creating busybox_busybox_1...
    wait for link.docker:1234

Then both containers should respond with the name of the container .<tld>, ex.:

.. code:: console

    @me ~$ ping link.docker -c 1
    PING link.docker (172.17.42.10) 56(84) bytes of data.
    64 bytes from 172.17.42.10: icmp_seq=1 ttl=64 time=0.075 ms
    ...

Stop
^^^^

You can remove or stop all the ``busybox`` project containers as follow:

.. code:: console

    @me ~$ bag8 rm busybox # or stop instead of rm
    Stopping busybox_busybox_1...
    Stopping busybox_link_1...
    Removing busybox_link_1...
    Removing busybox_busybox_1...

To remove, stop or start one container only of the ``busybox`` project, you
need to add the *-s* option to the bag8 corresponding command as follow:

.. code:: console

    @me ~$ bag8 stop busybox -s link
    Stopping busybox_link_1...

About projects
--------------

Let's say a project is a set of containers linked together to run a final app.
For example, the ``busybox`` project has two containers. The ``busybox`` up
when the required ``link`` container is up.

Default prefix
^^^^^^^^^^^^^^

We use the project name as prefix of the project container names, ex.:

.. code:: console

    @me ~$ docker ps
    CONTAINER ID  IMAGE         ...  NAMES
    28e0a48b30ec  bag8/busybox  ...  busybox_busybox_1
    fc7ff2358235  bag8/link     ...  busybox_link_1

Custom prefix
^^^^^^^^^^^^^

We can specify the prefix we want when we start a project, ex.:

.. code:: console

    @me ~$ bag8 up link -p bag8
    Creating bag8_link_1...

Reuse containers
^^^^^^^^^^^^^^^^

If containers with the same name are already running, ``bag8`` does not start
new ones. For example, if you re-run the command twice. It won't print nothing:

.. code:: console

    @me ~$ bag8 up link -p bag8

Mixing projects
^^^^^^^^^^^^^^^

Prefixing and reusing containers allow us to start several projects and mix
them all together. For example if we start the ``busybox`` we the same prefix
than ``link``, it will just link to the existing one:

.. code:: console

    @me ~$ bag8 up busybox -p bag8
    Creating bag8_busybox_1...

Etc.

Wise up
^^^^^^^

If you do not specify project name in your command, ``bag8`` will use your
current dir name as project name:

.. code:: console

    @me ~$ mkdir busybox
    @me ~$ cd busybox
    @me ~/busybox$ bag8 up
    Creating busybox_busybox_1...
    ...

Develop
-------

As we can see ``bag8`` is mostly oriented for development usage. Here we
introduce an additional feature named *develop*.

Let's you are in your development folder and you want to work with your local
code in your ``bag8`` environment. You can run the following command:

.. code:: console

    @me ~/busybox$ bag8 stop -s busybox # first we need to stop the previous container
    @me ~/busybox$ bag8 develop -c sh
    Creating busybox_busybox_1...
    / #

.. note:: By default develop command use bash interpreter to enter in the
          development container. Busybox doesn't have bash, so we had *- c*
          argument for the demo.

For the demo we mounted the ``/tmp`` folder of the busybox to the current dir.
It could have been your project sources. In practice, changes in the container
persist locally.

.. code:: console
    / # touch /tmp/this-is-a-demo
    / # exit
    @me ~/busybox$ ls
    this-is-a-demo


Nginx
-----

As developer tool, ``bag8`` helps in serving your services with nginx. Let's
say the busybox container is linked to a link container that listen on 1234.

.. code:: console

    @me ~/busybox$ bag up
    @me ~/busybox$ curl -I link.docker:1234
    HTTP/1.1 200 OK

You can write an nginx config for the busybox project that will proxy the link
service. Then by running the ``bag8 nginx`` command, the tool will copy the
config in a common folder and share it in the nginx container to start:

.. code:: console

    @me ~/busybox$ bag nginx
    @me ~/busybox$ curl -I busybox.nginx.docker
    HTTP/1.1 200 OK
    Server: nginx/1.9.11
    Date: Wed, 08 Jun 2016 21:32:10 GMT
    Connection: keep-alive


Dns
---

Bag8 uses `dnsdock` (cf.: https://github.com/tonistiigi/dnsdock) to help in
container `ip` resolution. Bag8 adds extra `DNSDOCK_ALIAS` environment variable
to each container. It permits to resolve the container `ip` from the host or
from another container.

To make it work, you need to setup your docker service and your network
properly.

First we suggest the following dnsmasq conf:

.. code:: console

    @me ~$ cat /etc/dnsmasq.d/50-docker
    bind-interfaces
    except-interface=docker0
    server=/docker/172.17.42.1

As suggested in the `dnsdock` page, you need the following `DOCKER_OPTS`:

.. code::

    DOCKER_OPTS="-bip 172.17.42.1/24 -dns 172.17.42.1"

At the end, to enable `dnsdock` and check you are resolving the busybox, you
can type the following commands:

.. code:: console

    @me ~$ bag8 dns # it pulls the dnsdock and runs it
    @me ~$ dig busybox.docker
    ; <<>> DiG 9.9.5-9+deb8u3-Debian <<>> busybox
    ...
    ;; QUESTION SECTION:
    ;busybox.docker.           IN  A

    ;; ANSWER SECTION:
    busybox.docker.        0   IN  A   172.17.42.204

