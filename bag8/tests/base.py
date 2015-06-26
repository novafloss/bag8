from __future__ import absolute_import, division, print_function, unicode_literals  # noqa

from subprocess import Popen
from subprocess import PIPE

from functools import partial

call = partial(Popen, stdout=PIPE, stderr=PIPE)
