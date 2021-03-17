from __future__ import absolute_import, division, print_function

__metaclass__ = type

from tempfile import NamedTemporaryFile
from os import chmod, path, remove, environ
from stat import S_IEXEC, S_IREAD, S_IWRITE
import json
import re
import io
from jinja2 import Template

def job_card_contents():
    JOB_CARD_TEMPLATE = """//{{ userid }}1  JOB CLASS={{ class }},MSGLEVEL=(1,1),MSGCLASS={{ msgclass }}
"""
    JOB_CARD_CONTENTS = Template(JOB_CARD_TEMPLATE).render({
        'userid': environ.get("FTP_USERID"),
        'class': environ.get("FTP_JOB_CLASS"),
        'msgclass': environ.get("FTP_JOB_MSGCLASS"),
    })
    return JOB_CARD_CONTENTS

def job_output(ftp, job_id=None, owner=None, job_name=None, dd_name=None):
    job_name = "*"
    owner = "*"
    dd_name = ""

    job_detail_json = _get_job_output(ftp, job_id, owner, job_name, dd_name)

    if len(job_detail_json) == 0:
        job_id = "" if job_id == "*" else job_id
        owner = "" if owner == "*" else owner
        job_name = "" if job_name == "*" else job_name
        job_detail_json = _get_job_output(ftp, job_id, owner, job_name, dd_name)

    for job in job_detail_json:
        job["ret_code"] = {} if job.get("ret_code") is None else job.get("ret_code")
        job["ret_code"]["code"] = _get_return_code_num(
            job.get("ret_code").get("msg", "")
        )
        job["ret_code"]["msg_code"] = _get_return_code_str(
            job.get("ret_code").get("msg", "")
        )
        job["ret_code"]["msg_txt"] = ""
        if job.get("ret_code").get("msg", "") == "":
            job["ret_code"]["msg"] = "AC"
    return job_detail_json

def _get_job_output(ftp, job_id="*", owner="*", job_name="*", dd_name=""):
    job_detail_json = {}
    rc, out, err = _get_job_output_str(ftp, job_id, owner, job_name, dd_name)

    if rc != 0:
        raise RuntimeError(
            "Failed to retrieve job output. RC: {0} Error: {1}".format(
                str(rc), str(err)
            )
        )
    if not out:
        raise RuntimeError("Failed to retrieve job output. No job output found.")
    job_detail_json = json.loads(out, strict=False)
    return job_detail_json

def _get_job_output_str(ftp, job_id="*", owner="*", job_name="*", dd_name=""):
    get_job_detail_json_jcl_template = """
//COPYREXX EXEC PGM=IEBGENER
//SYSUT2   DD DSN=&&REXXLIB(RXPGM),DISP=(NEW,PASS),
//         DCB=(DSORG=PO,LRECL=80,RECFM=FB),
//         SPACE=(TRK,(15,,1)),UNIT=3390
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//SYSUT1   DD *,DLM=AA
 /* REXX */
rc=isfcalls('ON')
jobid = strip('{{ job_id }}','L')
if (jobid <> '') then do
ISFFILTER='JobID EQ '||jobid
end
owner = strip('{{ owner }}','L')
if (owner <> '') then do
ISFOWNER=owner
end
jobname = strip('{{ jobname }}','L')
if (jobname <> '') then do
ISFPREFIX=jobname
end
ddname = strip('{{ ddname }}','L')
if (ddname == '?') then do
ddname = ''
end
Address SDSF "ISFEXEC ST (ALTERNATE DELAYED)"
if rc<>0 then do
Say '[]'
Exit 0
end
if isfrows == 0 then do
Say '[]'
end
else do
Say '['
do ix=1 to isfrows
    linecount = 0
    if ix<>1 then do
    Say ','
    end
    Say '{'
    Say '"'||'job_id'||'":"'||value('JOBID'||"."||ix)||'",'
    Say '"'||'job_name'||'":"'||value('JNAME'||"."||ix)||'",'
    Say '"'||'subsystem'||'":"'||value('ESYSID'||"."||ix)||'",'
    Say '"'||'owner'||'":"'||value('OWNERID'||"."||ix)||'",'
    Say '"'||'ret_code'||'":{"'||'msg'||'":"'||value('RETCODE'||"."||ix)||'"},'
    Say '"'||'class'||'":"'||value('JCLASS'||"."||ix)||'",'
    Say '"'||'content_type'||'":"'||value('JTYPE'||"."||ix)||'",'
    Address SDSF "ISFACT ST TOKEN('"TOKEN.ix"') PARM(NP ?)",
"("prefix JDS_
    lrc=rc
    if lrc<>0 | JDS_DDNAME.0 == 0 then do
    Say '"ddnames":[]'
    end
    else do
    Say '"ddnames":['
    do jx=1 to JDS_DDNAME.0
        if jx<>1 & ddname == '' then do
        Say ','
        end
        if ddname == '' | ddname == value('JDS_DDNAME'||"."||jx) then do
        Say '{'
        Say '"'||'ddname'||'":"'||value('JDS_DDNAME'||"."||jx)||'",'
        Say '"'||'record_count'||'":"'||value('JDS_RECCNT'||"."||jx)||'",'
        Say '"'||'id'||'":"'||value('JDS_DSID'||"."||jx)||'",'
        Say '"'||'stepname'||'":"'||value('JDS_STEPN'||"."||jx)||'",'
        Say '"'||'procstep'||'":"'||value('JDS_PROCS'||"."||jx)||'",'
        Say '"'||'byte_count'||'":"'||value('JDS_BYTECNT'||"."||jx)||'",'
        Say '"'||'content'||'":['
        Address SDSF "ISFBROWSE ST TOKEN('"token.ix"')"
        untilline = linecount + JDS_RECCNT.jx
        startingcount = linecount + 1
        do kx=linecount+1 to  untilline
            if kx<>startingcount then do
            Say ','
            end
            linecount = linecount + 1
            Say '"'||escapeNewLine(escapeDoubleQuote(isfline.kx))||'"'
        end
        Say ']'
        Say '}'
        end
        else do
            linecount = linecount + JDS_RECCNT.jx
        end
    end
    Say ']'
    end
    Say '}'
end
Say ']'
end
rc=isfcalls('OFF')
return 0
escapeDoubleQuote: Procedure
Parse Arg string
out=''
Do While Pos('"',string)<>0
Parse Var string prefix '"' string
out=out||prefix||'\\"'
End
Return out||string
escapeNewLine: Procedure
Parse Arg string
Return translate(string, '4040'x, '1525'x)
AA
//* -------------------------------------------------------------------
//STEP0    EXEC PGM=IKJEFT01,PARM='%RXPGM'
//SYSTSPRT DD SYSOUT=*
//SYSPROC  DD DISP=(OLD,DELETE),DSN=&&REXXLIB
//SYSTSIN  DD DUMMY
"""
    try:
        get_job_detail_json_jcl = job_card_contents() + Template(get_job_detail_json_jcl_template).render({'job_id': job_id, 'owner': owner, 'job_name': job_name, 'dd_name': dd_name})
        with io.BytesIO(bytes(get_job_detail_json_jcl, "utf-8")) as f:
            stdout = ftp.storlines("STOR JCL", f)
        get_job_detail_json_job_id = re.search(r'JOB\d{5}', stdout).group()

        lines = []
        ftp.retrlines("RETR " + get_job_detail_json_job_id + ".5", lines.append)
        lines[-1] = ""
        lines[-2] = ""
        joblog = ""
        for line in lines:
             joblog = joblog + line[1:] + "\n"

        rc, out, err = 0, joblog, ""
    except Exception:
        raise
    return rc, out, err

def _get_return_code_num(rc_str):
    """Parse an integer return code from
    z/OS job output return code string.
    Arguments:
        rc_str {str} -- The return code message from z/OS job log (eg. "CC 0000")
    Returns:
        Union[int, NoneType] -- Returns integer RC if possible, if not returns NoneType
    """
    rc = None
    match = re.search(r"\s*CC\s*([0-9]+)", rc_str)
    if match:
        rc = int(match.group(1))
    return rc

def _get_return_code_str(rc_str):
    """Parse an integer return code from
    z/OS job output return code string.
    Arguments:
        rc_str {str} -- The return code message from z/OS job log (eg. "CC 0000" or "ABEND")
    Returns:
        Union[str, NoneType] -- Returns string RC or ABEND code if possible, if not returns NoneType
    """
    rc = None
    match = re.search(r"(?:\s*CC\s*([0-9]+))|(?:ABEND\s*((?:S|U)[0-9]+))", rc_str)
    if match:
        rc = match.group(1) or match.group(2)
    return rc


def _ddname_pattern(contents, resolve_dependencies):
    """Resolver for ddname_pattern type arguments
    Arguments:
        contents {bool} -- The contents of the argument.
        resolved_dependencies {dict} -- Contains all of the dependencies and their contents,
        which have already been handled,
        for use during current arguments handling operations.
    Raises:
        ValueError: When contents is invalid argument type
    Returns:
        str -- The arguments contents after any necessary operations.
    """
    if not re.fullmatch(
        r"^(?:[A-Z]{1}[A-Z0-9]{0,7})|(?:\?{1})$", str(contents), re.IGNORECASE,
    ):
        raise ValueError(
            'Invalid argument type for "{0}". expected "ddname_pattern"'.format(
                contents
            )
        )
    return str(contents)
