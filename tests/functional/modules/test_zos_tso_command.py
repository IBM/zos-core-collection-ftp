from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import sys
import warnings

import ansible.constants
import ansible.errors
import ansible.utils
import pytest
from pprint import pprint

# The positive path test
def test_zos_tso_command_listuser(ansible_adhoc):
    hosts = ansible_adhoc(inventory='localhost', connection='local')
    print('--- hosts.all ---')
    pprint(hosts.all)
    pprint(hosts.all.options)
    pprint(vars(hosts.all.options['inventory_manager']))
    pprint(hosts.all.options['inventory_manager']._inventory.hosts)
    hosts.all.options['inventory_manager']._inventory.hosts
    results = hosts.localhost.zos_tso_command(commands=["LU DAIKI"])
    print('--- results.contacted ---')
    pprint(results.contacted)
    for result in results.contacted.values():
        assert result.get("output")[0].get("rc") == 0
        assert result.get("changed") is True
