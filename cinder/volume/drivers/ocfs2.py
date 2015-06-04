# Copyright (c) 2015 Servionica, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import errno
import os
import time

from oslo_concurrency import processutils as putils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import units
import six

from cinder.brick.localfs import localfs as localfs_brick

from cinder import exception
from cinder.i18n import _, _LE, _LI, _LW
from cinder.image import image_utils
from cinder import utils
from cinder.volume.drivers import remotefs

VERSION = '1.0.0'

LOG = logging.getLogger(__name__)

ocfs2_opts = [
    cfg.StrOpt('ocfs2_shares_config',
               default='/etc/cinder/ocfs2_shares',
               help='File with the list of available ocfs2 shares'),
    cfg.StrOpt('ocfs2_mount_point_base',
               default='$state_path/mnt',
               help=('Base dir containing mount points for ocfs2 shares.')),
    cfg.StrOpt('ocfs2_mount_options',
               default=None,
               help=('Mount options passed to the ocfs2 client. See section'
                     ' of the ocfs2 man page for details.')),
    cfg.IntOpt('ocfs2_mount_attempts',
               default=3,
               help=('The number of attempts to mount ocfs2 shares before '
                     'raising an error.  At least one attempt will be '
                     'made to mount an ocfs2 share, regardless of the '
                     'value specified.')),
]

CONF = cfg.CONF
CONF.register_opts(ocfs2_opts)


class Ocfs2Driver(remotefs.RemoteFSDriver):

    """Local file system based driver. Creates file on ocfs2 share for using
    it as a block device on hypervisor.
    """

    driver_volume_type = 'ocfs2'
    driver_prefix = 'ocfs2'
    volume_backend_name = 'Generic_ocfs2'
    VERSION = VERSION

    def __init__(self, execute=putils.execute, *args, **kwargs):
        self._ocfs2client = None
        super(Ocfs2Driver, self).__init__(*args, **kwargs)
        self.configuration.append_config_values(ocfs2_opts)
        root_helper = utils.get_root_helper()

        self.base = getattr(self.configuration,
                            'ocfs2_mount_point_base',
                            CONF.ocfs2_mount_point_base)
        self.base = os.path.realpath(self.base)

        opts = getattr(self.configuration,
                       'ocfs2_mount_options',
                       CONF.ocfs2_mount_options)

        self._ocfs2client = localfs_brick.Ocfs2Client(
            driver_volume_type, root_helper, execute=execute,
            ocfs2_mount_point_base=self.base,
            ocfs2_mount_options=opts)

    def set_execute(self, execute):
        super(Ocfs2Driver, self).set_execute(execute)
        if self._ocfs2client:
            self._ocfs2client.set_execute(execute)

    def do_setup(self, context):
        """Any initialization the volume driver does while starting."""
        super(Ocfs2Driver, self).do_setup(context)

        config = self.configuration.ocfs2_shares_config
        if not config:
            msg = (_("There's no ocfs2 config file configured (%s)") %
                   'ocfs2_shares_config')
            LOG.warn(msg)
            raise exception.Ocfs2Exception(msg)
