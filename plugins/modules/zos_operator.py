from ansible.module_utils.basic import AnsibleModule
from os import chmod
from os import environ
from tempfile import NamedTemporaryFile
import json
from stat import S_IEXEC, S_IREAD, S_IWRITE
from jinja2 import Template

def run_operator_command(command, module):
    jcl_template = """
//DAIKI1  JOB CLASS=A,MSGLEVEL=(1,1),MSGCLASS=K
//COPYREXX EXEC PGM=IEBGENER
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
    rc, stdout, stderr = run_commands(jcl_template, command, module)
    command_detail_json = json.loads(stdout, strict=False)
    return command_detail_json

def run_commands(jcl_template, command, module):
    delete_on_close = True
    dump_file = NamedTemporaryFile(delete=delete_on_close)

    script_template = """#!/bin/bash
/usr/bin/curl -D {{ dump_filename }} -B -u {{ ftp_userid }}:{{ ftp_password }} ftp://{{ ftp_host }} --quote "SITE FILETYPE=JES" --upload-file $1
jobid=`grep -oP "JOB\d{5}" {{ dump_filename }}`
/usr/bin/curl -B -u {{ ftp_userid }}:{{ ftp_password }} ftp://{{ ftp_host }}/$jobid.5 --quote "SITE FILETYPE=JES" | cut -c 2- | /usr/bin/head -n -2
"""
    script = Template(script_template).render({'dump_filename': dump_file.name, 'ftp_userid': environ.get('FTP_USERID'), 'ftp_password': environ.get('FTP_PASSWORD'), 'ftp_host': environ.get('FTP_HOST')})
    script_file = NamedTemporaryFile(delete=delete_on_close)
    with open(script_file.name, "w") as f:
        f.write(script)
    chmod(script_file.name, S_IEXEC | S_IREAD | S_IWRITE)
    script_file.file.close()

    jcl = Template(jcl_template).render({'command_str': command})
    jcl_file = NamedTemporaryFile(delete=delete_on_close)
    with open(jcl_file.name, "w") as f:
        f.write(jcl)
    rc, stdout, stderr = module.run_command([script_file.name, jcl_file.name])
    return rc, stdout, stderr

def run_module():
    module_args = dict(
        cmd=dict(type="str", required=True),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    result = dict(
        changed=False,
    )

    try:
        rc_message = run_operator_command(module.params["cmd"], module)
        result["rc"] = rc_message.get("rc")
        result["content"] = rc_message.get("content")
    except Exception as e:
        module.fail_json(
            msg="An unexpected error occurred: {0}".format(repr(e)), **result
        )
    result["changed"] = True
    module.exit_json(**result)


def main():
    run_module()

if __name__ == "__main__":
    main()

