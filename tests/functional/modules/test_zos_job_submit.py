from __future__ import absolute_import, division, print_function

__metaclass__ = type

from os import environ
import sys
import warnings

import ansible.constants
import ansible.errors
import ansible.utils
import pytest
from shellescape import quote
from pprint import pprint
from jinja2 import Template

JOB_CARD_TEMPLATE = """//{{ userid }}1  JOB CLASS={{ class }},MSGLEVEL=(1,1),MSGCLASS={{ msgclass }}
"""
JOB_CARD_CONTENTS = Template(JOB_CARD_TEMPLATE).render({
    'userid': environ.get("FTP_USERID").upper(),
    'class': environ.get("FTP_JOB_CLASS").upper(),
    'msgclass': environ.get("FTP_JOB_MSGCLASS").upper(),
})
JCL_FILE_CONTENTS = """
//UPTIME  EXEC PGM=BPXBATCH,
//        PARM='SH uptime'
//STDIN  DD DUMMY
//STDOUT DD SYSOUT=*
//STDERR DD SYSOUT=*
"""
TEMP_PATH = "/tmp/ansible/jcl"

# The positive path test
def test_zos_job_submit_positive_path(ansible_adhoc):
    hosts = ansible_adhoc(inventory='localhost', connection='local')
    hosts.localhost.file(path=TEMP_PATH, state="directory")
    hosts.localhost.shell(
            cmd="echo {0} > {1}/SAMPLE".format(quote(JOB_CARD_CONTENTS + JCL_FILE_CONTENTS), TEMP_PATH)
    )
    print('--- hosts.all ---')
    pprint(hosts.all)
    pprint(hosts.all.options)
    pprint(vars(hosts.all.options['inventory_manager']))
    pprint(hosts.all.options['inventory_manager']._inventory.hosts)
    hosts.all.options['inventory_manager']._inventory.hosts
    results = hosts.localhost.zos_job_submit(src="{0}/SAMPLE".format(TEMP_PATH), location="LOCAL", wait=True, wait_time_s=10)
    print('--- results.contacted ---')
    pprint(results.contacted)
    for result in results.contacted.values():
        assert result["jobs"][0]["ret_code"]["code"] == 0
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
        assert result["jobs"][0]["ret_code"]["code"] == 0
        assert result.get("changed") is True
    #    assert result.get("content") is not None

def test_zos_job_submit_uss_S013(ansible_adhoc):
    hosts = ansible_adhoc(inventory='localhost', connection='local')
    print('--- hosts.all ---')
    pprint(hosts.all)
    pprint(hosts.all.options)
    pprint(vars(hosts.all.options['inventory_manager']))
    pprint(hosts.all.options['inventory_manager']._inventory.hosts)
    hosts.all.options['inventory_manager']._inventory.hosts
    results = hosts.localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(S013JOB)", location="DATA_SET")
    print('--- results.contacted ---')
    pprint(results.contacted)
    for result in results.contacted.values():
        assert result["jobs"][0]["ret_code"]["msg"] == "ABEND S013"
        assert result["jobs"][0]["ret_code"]["msg_code"] == "S013"
        assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
        assert result.get("changed") is False 

def test_zos_job_submit_uss_long_job(ansible_adhoc):
    hosts = ansible_adhoc(inventory='localhost', connection='local')
    print('--- hosts.all ---')
    pprint(hosts.all)
    pprint(hosts.all.options)
    pprint(vars(hosts.all.options['inventory_manager']))
    pprint(hosts.all.options['inventory_manager']._inventory.hosts)
    hosts.all.options['inventory_manager']._inventory.hosts
    results = hosts.localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(SLEEP50)", location="DATA_SET", wait=True,wait_time_s=5)
    print('--- results.contacted ---')
    pprint(results.contacted)
    for result in results.contacted.values():
        assert result["jobs"][0]["ret_code"]["msg"] == "JOB NOT FOUND"
        assert result["jobs"][0]["ret_code"]["msg_code"] == "NOT FOUND"
        assert result["jobs"][0]["ret_code"]["msg_txt"] == "The job could not be found"

