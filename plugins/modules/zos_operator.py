import io
import re
from ftplib import FTP
from ansible.module_utils.basic import AnsibleModule
from ..module_utils.job import job_card_contents
from os import chmod
from os import environ
from tempfile import NamedTemporaryFile
import json
from stat import S_IEXEC, S_IREAD, S_IWRITE
from jinja2 import Template
import socks
import socket

def run_operator_command(ftp, command, module):
    jcl_template = """//COPYREXX EXEC PGM=IEBGENER
//SYSUT2   DD DSN=&&REXXLIB(RXPGM),DISP=(NEW,PASS),
//         DCB=(DSORG=PO,LRECL=80,RECFM=FB),
//         SPACE=(TRK,(15,,1)),UNIT=3390
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//SYSUT1   DD *,DLM=AA
 /* REXX */
rc=isfcalls('ON')
ISFCONS = "@ANSIBLE"
ISFDELAY = 1
ADDRESS SDSF ISFEXEC "'/{{ command_str }}'"

say '{"rc" : 'RC','
say ' "content": ['
if ISFULOG.0 > 0 then do
  do j = 3 to ISFULOG.0
    if j == ISFULOG.0
      then say ' "'ISFULOG.j '"'
    else
      say ' "'ISFULOG.j '",'
  end
end

say ']'
say '}'
rc=isfcalls('OFF')
exit
AA
//* ------------------------------------------------------------------- 
//STEP0    EXEC PGM=IKJEFT01,PARM='%RXPGM'
//SYSTSPRT DD SYSOUT=*
//SYSPROC  DD DISP=(OLD,DELETE),DSN=&&REXXLIB
//SYSTSIN  DD DUMMY
"""
    stdout = run_commands(ftp, jcl_template, command, module)
    command_detail_json = json.loads(stdout, strict=False)
    return command_detail_json

def run_commands(ftp, wrapper_jcl_template, command, module):
    # Submit the wrapper jcl to execute the tso command
    wrapper_jcl = job_card_contents() + Template(wrapper_jcl_template).render({'command_str': command})
    with io.BytesIO(bytes(wrapper_jcl, "utf-8")) as f:
        stdout = ftp.storlines("STOR JCL", f)

    # Get the jobid
    wrapper_jcl_jobId = re.search(r'JOB\d{5}', stdout).group()

    # Get the job log with the jobid
    joblog = []
    ftp.retrlines("RETR " + wrapper_jcl_jobId + ".5", joblog.append)

    # Get the output from the job log by deleting the last two lines and the first character
    del joblog[-2:]
    output = []
    for line in joblog:
        output.append(line[1:])
    return "\n".join(output)

def run_module():
    module_args = dict(
        cmd=dict(type="str", required=True),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    result = dict(
        changed=False,
    )

    if environ.get('FTP_SOCKS_PORT'):
       socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", int(environ.get('FTP_SOCKS_PORT')))
       socket.socket = socks.socksocket

    try:
       ftp = FTP()
       ftp.connect(environ.get('FTP_HOST'), int(environ.get('FTP_PORT') or 21))
       ftp.login(environ.get('FTP_USERID'), environ.get('FTP_PASSWORD'))
       ftp.sendcmd("site filetype=jes")

    except Exception as e:
       module.fail_json(
           msg="An unexpected error occurred during FTP login: {0}".format(repr(e)), **result
       )

    try:
        rc_message = run_operator_command(ftp, module.params["cmd"], module)
        result["rc"] = rc_message.get("rc")
        result["content"] = rc_message.get("content")
    except Exception as e:
        ftp.quit()
        module.fail_json(
            msg="An unexpected error occurred: {0}".format(repr(e)), **result
        )
    result["changed"] = True
    ftp.quit()
    module.exit_json(**result)


def main():
    run_module()

if __name__ == "__main__":
    main()

