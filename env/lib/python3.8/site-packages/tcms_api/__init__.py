# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Python API for the Kiwi TCMS test case management system.
#   Copyright (c) 2012 Red Hat, Inc. All rights reserved.
#   Author: Petr Splichal <psplicha@redhat.com>
#
#   Copyright (c) 2018,2020-2021 Kiwi TCMS project. All rights reserved.
#   Author: Alexander Todorov <info@kiwitcms.org>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
This module provides a dictionary based Python interface for the
Kiwi TCMS test case management system.

Installation::

    pip install tcms-api

Minimal config file ``~/.tcms.conf``::

    [tcms]
    url = https://tcms.server/xml-rpc/
    username = your-username
    password = your-password

For Kerberos specify the ``use_kerberos = True`` key without username
and password! Also make sure that your ``/etc/krb5.conf`` contains::

    [libdefaults]
    default_realm = .EXAMPLE.COM

where ``EXAMPLE.COM`` matches the realm in your organization.


.. important::

    The filename ``~/.tcms.conf`` is expanded to something like
    ``/home/tcms-bot/.tcms.conf`` on Linux and
    ``C:\\Users\\tcms-bot\\.tcms.conf`` on Windows, where ``tcms-bot``
    is the username on the local computer.

    It's also possible to provide system-wide config in ``/etc/tcms.conf``,
    which is valid only on Linux!

    Execute the following Python snippet to find the exact location on your
    system::

        import os
        print(os.path.expanduser('~/.tcms.conf'))

Connect to backend::

    from tcms_api import TCMS

    rpc_client = TCMS()

    for test_case in rpc_client.exec.TestCase.filter({'pk': 46490}):
        print(test_case)

.. important::

    For a list of available RPC methods see
    https://kiwitcms.readthedocs.io/en/latest/modules/tcms.rpc.api.html

    Example(s) and API scripts contributed by the Kiwi TCMS community
    can be found at https://github.com/kiwitcms/api-scripts. You are welcome
    to open a pull request with your own examples!

"""
import os
from configparser import ConfigParser
from distutils.util import strtobool

from tcms_api.xmlrpc import TCMSXmlrpc, TCMSKerbXmlrpc


class TCMS:  # pylint: disable=too-few-public-methods
    """
    Takes care of initiating the connection to the TCMS server and
    parses user configuration.
    """

    _connection = None
    _path = os.path.expanduser("~/.tcms.conf")

    def __init__(self):
        # Connect to the server unless already connected
        if TCMS._connection is not None:
            return

        # Try system settings when the config does not exist in user directory
        if not os.path.exists(self._path):
            self._path = "/etc/tcms.conf"
        if not os.path.exists(self._path):
            raise Exception(f"Config file '{self._path}' not found")

        config = ConfigParser()
        config.read(self._path)

        # Make sure the server URL is set
        try:
            config['tcms']['url'] is not None
        except (KeyError, AttributeError) as err:
            raise Exception(f"No url found in {self._path}") from err

        if strtobool(config['tcms'].get('use_kerberos', 'False')):
            # use Kerberos
            TCMS._connection = TCMSKerbXmlrpc(None, None,
                                              config['tcms']['url']).server
            return

        try:
            # use password authentication
            TCMS._connection = TCMSXmlrpc(config['tcms']['username'],
                                          config['tcms']['password'],
                                          config['tcms']['url']).server
        except KeyError as err:
            raise Exception(
                f"username/password required in {self._path}") from err

        return

    @property
    def exec(self):
        """
        Property that returns the underlying XML-RPC connection on which
        you can call various server-side functions.
        """
        return TCMS._connection
