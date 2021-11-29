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

def test_zos_job_output_ftp(localhost, ansible_adhoc):
    store_jcl(localhost, "sample.jcl")
    result = localhost.zos_job_submit(src="{0}/SAMPLE".format(TEMP_PATH), location="LOCAL", wait=True).localhost

    print('--- result for zos_job_submit ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == 0
    assert result["jobs"][0]["ret_code"]["msg"] == "CC 0000"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "0000"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert result.is_changed
    assert result.is_successful

    job_id = result["jobs"][0]["job_id"]

    result = localhost.zos_job_output(job_id=job_id).localhost

    print('--- result for zos_job_output --- ')
    pprint(result)

    assert result["jobs"][0]["job_id"] == job_id


def test_zos_job_output_pds(localhost, ansible_adhoc):
    result = localhost.zos_job_submit(src="DAIKI.ANSIBLE.PDS(SAMPLE)", location="DATA_SET", wait=True).localhost

    print('--- result ---')
    pprint(result)

    assert result["jobs"][0]["ret_code"]["code"] == 0
    assert result["jobs"][0]["ret_code"]["msg"] == "CC 0000"
    assert result["jobs"][0]["ret_code"]["msg_code"] == "0000"
    assert result["jobs"][0]["ret_code"]["msg_txt"] == ""
    assert result.is_changed
    assert result.is_successful

    job_id = result["jobs"][0]["job_id"]

    result = localhost.zos_job_output(job_id=job_id).localhost

    print('--- result for zos_job_output --- ')
    pprint(result)

    assert result["jobs"][0]["job_id"] == job_id
