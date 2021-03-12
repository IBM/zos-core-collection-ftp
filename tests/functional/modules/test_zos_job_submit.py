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
def test_zos_job_submit_positive_path(ansible_adhoc):
    hosts = ansible_adhoc(inventory='localhost', connection='local')
    print('--- hosts.all ---')
    pprint(hosts.all)
    pprint(hosts.all.options)
    pprint(vars(hosts.all.options['inventory_manager']))
    pprint(hosts.all.options['inventory_manager']._inventory.hosts)
    hosts.all.options['inventory_manager']._inventory.hosts
    results = hosts.localhost.zos_job_submit(src="/root/sample.txt", location="LOCAL", wait=True, wait_time_s=10)
    print('--- results.contacted ---')
    pprint(results.contacted)
    for result in results.contacted.values():
        assert result["rc"] == 0
        assert result.get("changed") is True
    #    assert result.get("content") is not None


def test_zos_job_submit_uss(ansible_adhoc):
    hosts = ansible_adhoc(inventory='localhost', connection='local')
    print('--- hosts.all ---')
    pprint(hosts.all)
    pprint(hosts.all.options)
    pprint(vars(hosts.all.options['inventory_manager']))
    pprint(hosts.all.options['inventory_manager']._inventory.hosts)
    hosts.all.options['inventory_manager']._inventory.hosts
    results = hosts.localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(SAMPLE)", location="DATA_SET")
    print('--- results.contacted ---')
    pprint(results.contacted)
    for result in results.contacted.values():
        assert result["rc"] == 0
        assert result.get("changed") is True
    #    assert result.get("content") is not None
