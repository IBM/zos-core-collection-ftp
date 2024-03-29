import io
import re
from ftplib import FTP
from ansible.module_utils.basic import AnsibleModule
from ..module_utils.job import job_card_contents, wait_jobs_completion
from os import chmod, environ, path
from tempfile import NamedTemporaryFile
import json
from stat import S_IEXEC, S_IREAD, S_IWRITE
from jinja2 import Template

def run_tso_command(ftp, commands, module):
    jcl_template = """//COPYREXX EXEC PGM=IEBGENER
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
    stdout = run_commands(ftp, jcl_template, commands, module)
    command_detail_json = json.loads(stdout, strict=False)
    return command_detail_json

def run_commands(ftp, wrapper_jcl_template, commands, module):
    command_str = ""
    for item in commands:
      command_str = command_str + item + ";"

    # Submit the wrapper jcl to execute the tso command
    wrapper_jcl = job_card_contents() + Template(wrapper_jcl_template).render({'command_str': command_str})
    delete_on_close = True
    wrapper_jcl_file = NamedTemporaryFile(delete=delete_on_close)
    with open(wrapper_jcl_file.name, 'w')  as f:
        f.write(wrapper_jcl)
    with open(wrapper_jcl_file.name, 'rb') as f:
        stdout = ftp.storlines("STOR JCL", f)

    # Get the jobid
    wrapper_jcl_jobId = re.search(r'JOB\d{5}', stdout).group()

    # Wait for the job completion
    wait_jobs_completion(ftp, wrapper_jcl_jobId, 10)

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
        commands=dict(type="raw", required=True, aliases=["command"]),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    result = dict(
        changed=False,
    )

    commands = module.params['commands']

    if environ.get('FTP_SOCKS_PORT'):
       import socks
       import socket
       socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", int(environ.get('FTP_SOCKS_PORT')))
       socket.socket = socks.socksocket

    try:
       if environ.get('FTP_TLS_VERSION'):
           from ftplib import FTP_TLS
           import ssl
           cert_file_path = environ.get('FTP_TLS_CERT_FILE')
           if cert_file_path:
               if not path.isfile(cert_file_path):
                   module.fail_json(
                       msg="Certification file not found: {0}".format(repr(cert_file_path)), **result
                   )
               context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
               context.load_verify_locations(cert_file_path)
               context.check_hostname = False
               ftp = FTP_TLS(context=context)
           else:
               ftp = FTP_TLS()
           tls_version = environ.get('FTP_TLS_VERSION')
           if tls_version == '1.2':
               ftp.ssl_version = ssl.PROTOCOL_TLSv1_2
       else:
           ftp = FTP()
       ftp.connect(environ.get('FTP_HOST'), int(environ.get('FTP_PORT') or 21))
       ftp.login(environ.get('FTP_USERID'), environ.get('FTP_PASSWORD'))
       ftp.sendcmd("site filetype=jes")
       ftp.set_pasv(True)

       if environ.get('FTP_TLS_VERSION'):
           ftp.prot_p()

    except Exception as e:
       module.fail_json(
           msg="An unexpected error occurred during FTP login: {0}".format(repr(e)), **result
       )

    try:
        result = run_tso_command(ftp, commands, module)
        ftp.quit()
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
        ftp.quit()
        module.fail_json(
            msg="An unexpected error occurred: {0}".format(repr(e)), **result
        )

def main():
    run_module()

if __name__ == "__main__":
    main()

