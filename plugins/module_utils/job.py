from __future__ import absolute_import, division, print_function

__metaclass__ = type

from tempfile import NamedTemporaryFile
from os import chmod, path, remove, environ
from stat import S_IEXEC, S_IREAD, S_IWRITE
from timeit import default_timer as timer
import re
import io
from jinja2 import Template
from time import sleep
from six import PY2

def job_card_contents():
    """Generate a job card from the environment variables.

    Returns:
        String -- the job card
    """
    job_card_template = """//{{ userid }}1  JOB CLASS={{ class }},MSGLEVEL=(1,1),MSGCLASS={{ msgclass }}

"""
    job_card_contens = Template(job_card_template).render({
        'userid': environ.get("FTP_USERID").upper(),
        'class': environ.get("FTP_JOB_CLASS").upper(),
        'msgclass': environ.get("FTP_JOB_MSGCLASS").upper(),
    })
    return job_card_contens

def job_output(ftp, wait_time_s, job_id=None, owner=None, job_name=None, dd_name=None):
    """Get the output from a z/OS job based on various search criteria.
    Keyword Arguments:
        ftp {ftplib} -- The instance of FTP class
        job_id {str} -- The job ID to search for (default: {None})
        owner {str} -- The owner of the job (default: {None})
        job_name {str} -- The job name search for (default: {None})
        dd_name {str} -- The data definition to retrieve (default: {None})

    Raises:
        RuntimeError: When job output cannot be retrieved successfully but job exists.
        RuntimeError: When no job output is found

    Returns:
        list[dict] -- The output information for a list of jobs matching specified criteria.
    """
    job_id = job_id or "*"
    owner = owner or "*"
    job_name = job_name or "*"
    dd_name = dd_name or ""

    job_detail = _get_job_output(ftp, wait_time_s, job_id, owner, job_name, dd_name)

    if len(job_detail) == 0:
        job_id = "" if job_id == "*" else job_id
        owner = "" if owner == "*" else owner
        job_name = "" if job_name == "*" else job_name
        job_detail = _get_job_output(ftp, wait_time_s, job_id, owner, job_name, dd_name)
    return job_detail


def _get_job_output(ftp, wait_time_s, job_id="*", owner="*", job_name="*", dd_name=""):
    rc, out, err = _get_job_output_str(ftp, wait_time_s, job_id, owner, job_name, dd_name)
    if rc != 0:
        raise RuntimeError(
            "Failed to retrieve job output. RC: {0} Error: {1}".format(
                str(rc), str(err)
            )
        )
    jobs = []
    if out:
        jobs = _parse_jobs(out)
    if not jobs:
        jobs = _job_not_found(job_id, owner, job_name, dd_name)

    return jobs


def _job_not_found(job_id, owner, job_name, dd_name, ovrr=None):
    jobs = []

    job = {}

    job["job_id"] = job_id
    job["job_name"] = job_name
    job["subsystem"] = None
    job["system"] = None
    job["owner"] = None

    job["ret_code"] = {}
    job["ret_code"]["msg"] = "JOB NOT FOUND"
    job["ret_code"]["code"] = None
    job["ret_code"]["msg_code"] = "NOT FOUND"
    job["ret_code"]["msg_txt"] = "The job could not be found"

    job["class"] = ""
    job["content_type"] = ""

    job["ddnames"] = []
    dd = {}
    dd["ddname"] = dd_name
    dd["record_count"] = "0"
    dd["id"] = ""
    dd["stepname"] = None
    dd["procstep"] = ""
    dd["byte_count"] = "0"
    job["ddnames"].append(dd)

    if ovrr is not None:
        job["ret_code"]["msg"] = "NO JOBS FOUND"
        job["ret_code"]["msg_code"] = "NOT FOUND"
        job["ret_code"]["msg_txt"] = "No jobs returned from query"

    jobs.append(job)

    return jobs


def _parse_jobs(output_str):
    """Parse the output of the job retrieving rexx script.

    Args:
        output_str (str): The output string of the job retrieving rexx script.

    Returns:
        list[dict]: A list of jobs and their attributes.

    Rais:
        Runtime error if output wasn't parseable
    """
    jobs = []
    if "-----NO JOBS FOUND-----" not in output_str:
        job_strs = re.findall(
            r"^-----START\sOF\sJOB-----\n(.*?)-----END\sOF\sJOB-----",
            output_str,
            re.MULTILINE | re.DOTALL,
        )
        for job_str in job_strs:
            job_info_match = re.search(
                (
                    r"\s*job_id:([^\n]*)\n\s*job_name:([^\n]*)\n\s*subsystem:([^\n]*)\n\s*system:([^\n]*)\n"
                    r"\s*owner:([^\n]*)\n\s*ret_code_msg:([^\n]*)\n\s*class:([^\n]*)\n\s*content_type:([^\n]*)"
                ),
                job_str,
            )
            if job_info_match is not None:
                job = {}

                job["job_id"] = job_info_match.group(1).strip()
                job["job_name"] = job_info_match.group(2).strip()
                job["subsystem"] = job_info_match.group(3).strip()
                job["system"] = job_info_match.group(4).strip()
                job["owner"] = job_info_match.group(5).strip()

                job["ret_code"] = {}
                ret_code_msg = job_info_match.group(6).strip()
                if ret_code_msg:
                    job["ret_code"]["msg"] = ret_code_msg
                job["ret_code"]["code"] = _get_return_code_num(ret_code_msg)
                job["ret_code"]["msg_code"] = _get_return_code_str(ret_code_msg)
                job["ret_code"]["msg_txt"] = ""
                if "JCL ERROR" in ret_code_msg:
                    job["ret_code"][
                        "msg_txt"
                    ] = "JCL Error detected.  Check the data dumps for more information."

                if ret_code_msg == "":
                    job["ret_code"]["msg"] = "AC"

                job["class"] = job_info_match.group(7).strip()
                job["content_type"] = job_info_match.group(8).strip()

                job["ddnames"] = _parse_dds(job_str)
                jobs.append(job)
    else:
        jobs = _job_not_found("", "", "", "notused")

    return jobs


def _parse_dds(job_str):
    """Parse the dd section of output of the job retrieving rexx script.

    Args:
        job_str (str): The output string for a particular job returned from job retrieving rexx script.

    Returns:
        list[dict]: A list of DDs and their attributes.
    """
    dds = []
    if "-----START OF DD NAMES-----" in job_str:
        dd_strs = re.findall(
            r"^-----START\sOF\sDD-----\n(.*?)-----END\sOF\sDD-----",
            job_str,
            re.MULTILINE | re.DOTALL,
        )
        for dd_str in dd_strs:
            dd = {}
            dd_info_match = re.search(
                (
                    r"ddname:([^\n]*)\nrecord_count:([^\n]*)\nid:([^\n]*)\nstepname:([^\n]*)\n"
                    r"procstep:([^\n]*)\nbyte_count:([^\n]*)"
                ),
                dd_str,
            )
            dd["ddname"] = dd_info_match.group(1).strip()
            dd["record_count"] = dd_info_match.group(2).strip()
            dd["id"] = dd_info_match.group(3).strip()
            dd["stepname"] = dd_info_match.group(4).strip()
            dd["procstep"] = dd_info_match.group(5).strip()
            dd["byte_count"] = dd_info_match.group(6).strip()
            content_str = re.search(
                r"^-----START\sOF\sCONTENT-----\n(.*?)\n-----END\sOF\sCONTENT-----",
                dd_str,
                re.MULTILINE | re.DOTALL,
            )
            if content_str is not None:
                dd["content"] = content_str.group(1).split("\n")
            dds.append(dd)
    return dds


def _get_job_output_str(ftp, wait_time_s, job_id="*", owner="*", job_name="*", dd_name=""):
    """Generate JSON output string containing Job info from SDSF.
    Writes a temporary REXX script to the USS filesystem to gather output.

    Keyword Arguments:
        job_id {str} -- The job ID to search for (default: {''})
        owner {str} -- The owner of the job (default: {''})
        job_name {str} -- The job name search for (default: {''})
        dd_name {str} -- The data definition to retrieve (default: {''})

    Returns:
        tuple[int, str, str] -- RC, STDOUT, and STDERR from the REXX script.
    """
    get_job_detail_jcl_template = """//COPYREXX EXEC PGM=IEBGENER
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
jobname = strip('{{ job_name }}','L')
if (jobname <> '') then do
ISFPREFIX=jobname
end
ddname = strip('{{ dd_name }}','L')
if (ddname == '?') then do
ddname = ''
end

Address SDSF "ISFEXEC ST (ALTERNATE DELAYED)"
if rc<>0 then do
Say '[]'
Exit 0
end
if isfrows == 0 then do
Say '-----NO JOBS FOUND-----'
end
else do
do ix=1 to isfrows
    linecount = 0

    Say '-----START OF JOB-----'
    Say 'job_id'||':'||value('JOBID'||"."||ix)
    Say 'job_name'||':'||value('JNAME'||"."||ix)
    Say 'subsystem'||':'||value('ESYSID'||"."||ix)
    Say 'system'||':'||value('SYSNAME'||"."||ix)
    Say 'owner'||':'||value('OWNERID'||"."||ix)
    Say 'ret_code_msg'||':'||value('RETCODE'||"."||ix)
    Say 'class'||':'||value('JCLASS'||"."||ix)
    Say 'content_type'||':'||value('JTYPE'||"."||ix)
    Address SDSF "ISFACT ST TOKEN('"TOKEN.ix"') PARM(NP ?)",
"("prefix JDS_
    lrc=rc
    if lrc<>0 | JDS_DDNAME.0 == 0 then do
    Say '-----NO DD NAMES FOUND-----'
    end
    else do
    Say '-----START OF DD NAMES-----'
    do jx=1 to JDS_DDNAME.0
        if ddname == '' | ddname == value('JDS_DDNAME'||"."||jx) then do
        Say '-----START OF DD-----'
        Say 'ddname'||':'||value('JDS_DDNAME'||"."||jx)
        Say 'record_count'||':'||value('JDS_RECCNT'||"."||jx)
        Say 'id'||':'||value('JDS_DSID'||"."||jx)
        Say 'stepname'||':'||value('JDS_STEPN'||"."||jx)
        Say 'procstep'||':'||value('JDS_PROCS'||"."||jx)
        Say 'byte_count'||':'||value('JDS_BYTECNT'||"."||jx)
        Say '-----START OF CONTENT-----'
        Address SDSF "ISFBROWSE ST TOKEN('"token.ix"')"
        untilline = linecount + JDS_RECCNT.jx
        startingcount = linecount + 1
        do kx=linecount+1 to  untilline
            linecount = linecount + 1
            Say isfline.kx
        end
        Say '-----END OF CONTENT-----'
        Say '-----END OF DD-----'
        end
    end
    Say '-----END OF DD NAMES-----'
    end
    Say '-----END OF JOB-----'
end
end

rc=isfcalls('OFF')

return 0
AA
//* -------------------------------------------------------------------
//STEP0    EXEC PGM=IKJEFT01,PARM='%RXPGM'
//SYSTSPRT DD SYSOUT=*
//SYSPROC  DD DISP=(OLD,DELETE),DSN=&&REXXLIB
//SYSTSIN  DD DUMMY
"""
    try:
        if dd_name is None or dd_name == "?":
            dd_name = ""
        get_job_detail_jcl = job_card_contents() + Template(get_job_detail_jcl_template).render({'job_id': job_id, 'owner': owner, 'job_name': job_name, 'dd_name': dd_name})
        delete_on_close = True
        get_job_detail_jcl_file = NamedTemporaryFile(delete=delete_on_close)
        with open(get_job_detail_jcl_file.name, 'w')  as f:
            f.write(get_job_detail_jcl)
        with open(get_job_detail_jcl_file.name, 'rb') as f:
            stdout = ftp.storlines("STOR JCL", f)
        get_job_detail_job_id = re.search(r'JOB\d{5}', stdout).group()

        # wait for the job completion
        duration = wait_jobs_completion(ftp, get_job_detail_job_id, wait_time_s)
        if duration >= wait_time_s:
           return 0, None, ""
        lines = []
        ftp.retrlines("RETR " + get_job_detail_job_id + ".5", lines.append)
        lines[-1] = ""
        lines[-2] = ""
        joblog = ""
        for line in lines:
             joblog = joblog + line[1:] + "\n"

        rc, out, err = 0, joblog, ""
    except Exception:
        raise
    return rc, out, err

def wait_jobs_completion(ftp, jobId, wait_time_s):
    starttime = timer()
    duration = 0
    jobs = []
    ftp.dir(jobs.append)
    while not re.search(jobId + '.*  OUTPUT', "\n".join(jobs)):
        sleep(0.5)
        checktime = timer()
        duration = round(checktime - starttime)
        if duration >= wait_time_s:
            break
        jobs = []
        ftp.dir(jobs.append)

    return duration

def job_status(ftp, job_id=None, owner=None, job_name=None):
    """Get the status information of a z/OS job based on various search criteria.

    Keyword Arguments:
        job_id {str} -- The job ID to search for (default: {None})
        owner {str} -- The owner of the job (default: {None})
        job_name {str} -- The job name search for (default: {None})

    Raises:
        RuntimeError: When job status cannot be retrieved successfully but job exists.
        RuntimeError: When no job status is found.

    Returns:
        list[dict] -- The status information for a list of jobs matching search criteria.
    """
    job_status = _get_job_status(ftp, job_id, owner, job_name)
    if len(job_status) == 0:
        job_id = "" if job_id == "*" else job_id
        job_name = "" if job_name == "*" else job_name
        owner = "" if owner == "*" else owner
        job_status = _get_job_status(job_id, owner, job_name)

    return job_status


def _get_job_status(ftp, job_id="*", owner="*", job_name="*"):
    rc, out, err = _get_job_status_str(ftp, job_id, owner, job_name)
    if rc != 0:
        raise RuntimeError(
            "Failed to retrieve job status. RC: {0} Error: {1}".format(
                str(rc), str(err)
            )
        )
    if out:
        jobs = _parse_jobs(out)
    if not out:
        jobs = _job_not_found(job_id, owner, job_name, "notused")

    for job in jobs:
        job.pop("ddnames", None)
    return jobs


def _get_job_status_str(job_id="*", owner="*", job_name="*"):
    """Generate JSON output string containing Job status info from SDSF.
    Writes a temporary REXX script to the USS filesystem to gather output.
    Keyword Arguments:
        job_id {str} -- The job ID to search for (default: {''})
        owner {str} -- The owner of the job (default: {''})
        job_name {str} -- The job name search for (default: {''})
    Returns:
        tuple[int, str, str] -- RC, STDOUT, and STDERR from the REXX script.
    """
    get_job_status_jcl_template = """
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
jobname = strip('{{ job_name }}','L')
if (jobname <> '') then do
ISFPREFIX=jobname
end
ddname = strip('{{ dd_name }}','L')
if (ddname == '?') then do
ddname = ''
end

Address SDSF "ISFEXEC ST (ALTERNATE DELAYED)"
if rc<>0 then do
Say '[]'
Exit 0
end
if isfrows == 0 then do
Say '-----NO JOBS FOUND-----'
end
else do
do ix=1 to isfrows
    linecount = 0
    if ix<>1 then do
    end
    Say '-----START OF JOB-----'
    Say 'job_id'||':'||value('JOBID'||"."||ix)
    Say 'job_name'||':'||value('JNAME'||"."||ix)
    Say 'subsystem'||':'||value('ESYSID'||"."||ix)
    Say 'system'||':'||value('SYSNAME'||"."||ix)
    Say 'owner'||':'||value('OWNERID'||"."||ix)
    Say 'ret_code_msg'||':'||value('RETCODE'||"."||ix)
    Say 'class'||':'||value('JCLASS'||"."||ix)
    Say 'content_type'||':'||value('JTYPE'||"."||ix)
    Say '-----END OF JOB-----'
end
end
rc=isfcalls('OFF')
return 0
"""
    try:
        if dd_name is None or dd_name == "?":
            dd_name = ""
        get_job_status_jcl = job_card_contents() + Template(get_job_status_jcl_template).render({'job_id': job_id, 'owner': owner, 'job_name': job_name, 'dd_name': dd_name})
        delete_on_close = True
        get_job_status_jcl_file = NamedTemporaryFile(delete=delete_on_close)
        with open(get_job_status_jcl_file.name, 'w')  as f:
            f.write(get_job_status_jcl)
        with open(get_job_status_jcl_file.name, 'rb') as f:
            stdout = ftp.storlines("STOR JCL", f)
        get_job_status_job_id = re.search(r'JOB\d{5}', stdout).group()

        lines = []
        ftp.retrlines("RETR " + get_job_status_job_id + ".5", lines.append)
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
    if PY2:
        if not re.match(
            r"^(?:[A-Z]{1}[A-Z0-9]{0,7})|(?:\?{1})$", str(contents), re.IGNORECASE,
        ):
            raise ValueError(
                'Invalid argument type for "{0}". expected "ddname_pattern"'.format(
                    contents
                )
            )
    else:
        if not re.fullmatch(
            r"^(?:[A-Z]{1}[A-Z0-9]{0,7})|(?:\?{1})$", str(contents), re.IGNORECASE,
        ):
            raise ValueError(
                'Invalid argument type for "{0}". expected "ddname_pattern"'.format(
                    contents
                )
            )
    return str(contents)
