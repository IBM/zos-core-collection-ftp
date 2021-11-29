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
TEMP_PATH = "/tmp/ansible/jcl"

def store_jcl(localhost, jcl_filename):
    with open("tests/functional/files/{0}".format(jcl_filename)) as f:
       jcl_file_content = f.read()

    localhost.file(path=TEMP_PATH, state="directory")
    localhost.shell(
            cmd="echo {0} > {1}/SAMPLE".format(quote(JOB_CARD_CONTENTS + jcl_file_content), TEMP_PATH)
    )

# The positive path test
def test_submit_ftp_jcl(localhost, ansible_adhoc):
    store_jcl(localhost, "sample.jcl")
    result = localhost.zos_job_submit(src="{0}/SAMPLE".format(TEMP_PATH), location="LOCAL", wait=True).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == 0
    assert result["jobs"][0]["ret_code"]["msg"] == "CC 0000"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "0000"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert result.is_changed
    assert result.is_successful

def test_submit_pds_jcl(localhost, ansible_adhoc):
    result = localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(SAMPLE)", location="DATA_SET", wait=True).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == 0
    assert result["jobs"][0]["ret_code"]["msg"] == "CC 0000"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "0000"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert result.is_changed
    assert result.is_successful

# The negative path test
def test_submit_ftp_jcl_RC12(localhost, ansible_adhoc):
    store_jcl(localhost, "RC12.jcl")
    result = localhost.zos_job_submit(src="{0}/SAMPLE".format(TEMP_PATH), location="LOCAL", wait=True).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == 12
    assert result["jobs"][0]["ret_code"]["msg"] == "CC 0012"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "0012"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert result.is_changed
    assert result.is_successful

def test_submit_pds_jcl_RC12(localhost, ansible_adhoc):
    result = localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(RC12)", location="DATA_SET", wait=True).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == 12
    assert result["jobs"][0]["ret_code"]["msg"] == "CC 0012"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "0012"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert result.is_changed
    assert result.is_successful

def test_submit_ftp_jcl_RC12_maxrc(localhost, ansible_adhoc):
    store_jcl(localhost, "RC12.jcl")
    result = localhost.zos_job_submit(src="{0}/SAMPLE".format(TEMP_PATH), location="LOCAL", wait=True, max_rc=0).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == 12
    assert result["jobs"][0]["ret_code"]["msg"] == "CC 0012"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "0012"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert result.is_changed
    assert result.is_failed

def test_submit_pds_jcl_RC12_maxrc(localhost, ansible_adhoc):
    result = localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(RC12)", location="DATA_SET", wait=True, max_rc=0).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == 12
    assert result["jobs"][0]["ret_code"]["msg"] == "CC 0012"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "0012"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert result.is_changed
    assert result.is_failed


def test_submit_pds_jcl_JCLERROR(localhost, ansible_adhoc):
    result = localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(JCLERROR)", location="DATA_SET", wait=True).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == None
    assert result["jobs"][0]["ret_code"]["msg"] == "JCL ERROR"
    assert result["jobs"][0]["ret_code"]["msg_code"] == None
    assert len(result["jobs"][0]["ret_code"]["msg_txt"]) > 0
    assert not result.is_changed
    assert result.is_failed

def test_submit_ftp_jcl_JCLERROR(localhost, ansible_adhoc):
    store_jcl(localhost, "JCLERROR.jcl")
    result = localhost.zos_job_submit(src="{0}/SAMPLE".format(TEMP_PATH), location="LOCAL", wait=True).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == None
    assert result["jobs"][0]["ret_code"]["msg"] == "JCL ERROR"
    assert result["jobs"][0]["ret_code"]["msg_code"] == None
    assert len(result["jobs"][0]["ret_code"]["msg_txt"]) > 0
    assert not result.is_changed
    assert result.is_failed

def test_submit_pds_jcl_Abend_S013(localhost, ansible_adhoc):
    result = localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(S013JOB)", location="DATA_SET", wait=True).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == None
    assert result["jobs"][0]["ret_code"]["msg"] == "ABEND S013"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "S013"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert not result.is_changed
    assert result.is_failed

def test_submit_ftp_jcl_Abend_S013(localhost, ansible_adhoc):
    store_jcl(localhost, "ABNDS013.jcl")
    result = localhost.zos_job_submit(src="{0}/SAMPLE".format(TEMP_PATH), location="LOCAL", wait=True).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == None
    assert result["jobs"][0]["ret_code"]["msg"] == "ABEND S013"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "S013"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert not result.is_changed
    assert result.is_failed

def test_submit_pds_jcl_long_job(localhost, ansible_adhoc):
    result = localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(SLEEP50)", location="DATA_SET", wait=True,wait_time_s=5).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == None
    assert result["jobs"][0]["ret_code"]["msg"] == "JOB NOT FOUND"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "NOT FOUND"
    assert "Timeout" in result["message"]["stdout"]
    assert result.is_changed
    assert result.is_successful

def test_submit_ftp_jcl_long_job(localhost, ansible_adhoc):
    store_jcl(localhost, "SLEEP50.jcl")
    result = localhost.zos_job_submit(src="{0}/SAMPLE".format(TEMP_PATH), location="LOCAL", wait=True, wait_time_s=5).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == None
    assert result["jobs"][0]["ret_code"]["msg"] == "JOB NOT FOUND"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "NOT FOUND"
    assert "Timeout" in result["message"]["stdout"]
    assert result.is_changed
    assert result.is_successful

