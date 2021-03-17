from ansible.module_utils.basic import AnsibleModule
from ..module_utils.job import job_card_contents
from os import chmod
from os import environ
from tempfile import NamedTemporaryFile
import json
from stat import S_IEXEC, S_IREAD, S_IWRITE
from jinja2 import Template

def run_tso_command(commands, module):
    jcl_template = """
//COPYREXX EXEC PGM=IEBGENER
//SYSUT2   DD DSN=&&REXXLIB(RXPGM),DISP=(NEW,PASS),
//         DCB=(DSORG=PO,LRECL=80,RECFM=FB),
//         SPACE=(TRK,(15,,1)),UNIT=3390
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//SYSUT1   DD *,DLM=AA
 /* REXX */
cmds = "{{ command_str }}"
ADDRESS TSO
say '{"output":['
do while cmds <> ''
  x = OUTTRAP("listcato.")
  i = 1
  say '{ '
  parse var  cmds cmd ';' cmds
  say ' "command" : "'cmd'",'
  no = POS(';', cmds)
  cmd
  say ' "rc" : 'RC','
  rc.i = RC
  i = i + 1
  say ' "lines" : 'listcato.0','
  say ' "content" : [ '
  do j = 1 to listcato.0
    if j == listcato.0
      then say ' "'listcato.j '"'
    else
      say ' "'listcato.j '",'
  end
  say ']'
  x = OUTTRAP("OFF")
  if no == 0
    then say '}'
  else
    say '},'
end
say ']'
say '}'
drop listcato.
AA
//* ------------------------------------------------------------------- 
//STEP0    EXEC PGM=IKJEFT01,PARM='%RXPGM'
//SYSTSPRT DD SYSOUT=*
//SYSPROC  DD DISP=(OLD,DELETE),DSN=&&REXXLIB
//SYSTSIN  DD DUMMY
"""
    rc, stdout, stderr = run_commands(jcl_template, commands, module)
    command_detail_json = json.loads(stdout, strict=False)
    return command_detail_json

def run_commands(jcl_template, commands, module):
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

    command_str = ""
    for item in commands:
      command_str = command_str + item + ";"
    jcl = job_card_contents() + Template(jcl_template).render({'command_str': command_str})
    jcl_file = NamedTemporaryFile(delete=delete_on_close)
    with open(jcl_file.name, "w") as f:
        f.write(jcl)
    rc, stdout, stderr = module.run_command([script_file.name, jcl_file.name])
    return rc, stdout, stderr

def run_module():
    module_args = dict(
        commands=dict(type="raw", required=True, aliases=["command"]),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    result = dict(
        changed=False,
    )

    commands = module.params['commands']

    try:
        result = run_tso_command(commands, module)
        for cmd in result.get("output"):
            if cmd.get("rc") != 0:
                module.fail_json(
                    msg='The TSO command "'
                    + cmd.get("command", "")
                    + '" execution failed.',
                    **result
                )

        result["changed"] = True
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(
            msg="An unexpected error occurred: {0}".format(repr(e)), **result
        )

def main():
    run_module()

if __name__ == "__main__":
    main()

