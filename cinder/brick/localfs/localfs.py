# Copyright (c) 2015 Servionica, Inc
# All Rights Reserved
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

"""Remote filesystem client utilities."""

import hashlib
import os
import re

from oslo_concurrency import processutils as putils
from oslo_log import log as logging
import six

from cinder.brick import exception
from cinder.brick.remotefs import remotefs
from cinder.i18n import _, _LI

LOG = logging.getLogger(__name__)


class LocalFsClient(remotefs.RemoteFsClient):

    def __init__(self, mount_type, root_helper,
                 execute=putils.execute, *args, **kwargs):
        self._mount_type = mount_type
        if mount_type == "ocfs2":
            self._mount_base = kwargs.get('ocfs2_mount_point_base', None)
            if not self._mount_base:
                raise exception.InvalidParameterValue(
                    err=_('ocfs2_mount_point_base required'))
            self._mount_options = kwargs.get('ocfs2_mount_options', None)
        if mount_type == "xfs":
            self._mount_base = kwargs.get('xfs_mount_point_base', None)
            if not self._mount_base:
                raise exception.InvalidParameterValue(
                    err=_('xfs_mount_point_base required'))
            self._mount_options = kwargs.get('xfs_mount_options', None)
        else:
            raise exception.ProtocolNotSupported(protocol=mount_type)
        self.root_helper = root_helper
        self.set_execute(execute)

    def mount(self, share, flags=None):
        """Mount given share."""
        mount_path = self.get_mount_point(share)

        if mount_path in self._read_mounts():
            LOG.info(_LI('Already mounted: %s') % mount_path)
            return

        self._execute('mkdir', '-p', mount_path, check_exit_code=0)
        if self._mount_type == 'ocfs2':
            # transform UUID into terminal option UUID=<uuid>
            share = 'UUID=%s' % share
            self._do_mount(self._mount_type, share, mount_path,
                           self._mount_options, flags)

    def _mount_ocfs2(self, ocfs2_share, mount_path, flags=None,
                     volume_uuid=None):
        """Mounts ocfs2 share based on the specified params."""
        mnt_cmd = ['mount', '-t', mount_type]
        if mount_options is not None:
            mnt_cmd.extend(['-o', mount_options])
        if volume_uuid:
            pass
        if flags is not None:
            mnt_cmd.extend(flags)
        mnt_cmd.extend([share, mount_path])

        self._execute(*mnt_cmd, root_helper=self.root_helper,
                      run_as_root=True, check_exit_code=0)
