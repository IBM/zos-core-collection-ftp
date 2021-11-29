from ansible.module_utils.basic import AnsibleModule
# from ansible_collections.ibm.ibm_zos_core_ftp.plugins.module_utils.job import job_output
from ..module_utils.job import job_output, job_card_contents, wait_jobs_completion
from tempfile import NamedTemporaryFile
from os import environ, path
import re
from stat import S_IEXEC, S_IREAD, S_IWRITE
from jinja2 import Template
from ftplib import FTP
import io

def run_module():
    module_args = dict(
        job_id=dict(type="str", required=False),
        job_name=dict(type="str", required=False),
        owner=dict(type="str", required=False),
        ddname=dict(type="str", required=False),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    job_id = module.params.get("job_id")
    job_name = module.params.get("job_name")
    owner = module.params.get("owner")
    ddname = module.params.get("ddname")

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
                       msg="The TLS cartificate file not found: {0}".format(repr(cert_file_path)), **result
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

    if not job_id and not job_name and not owner:
       module.fail_json(msg="Please provide a job_id or job_name or owner")

    try:
       result = {}
       wait_time_s = 10
       result["jobs"] = job_output(ftp, wait_time_s, job_id, owner, job_name, ddname)
       result["changed"] = False
    except Exception as e:
       module.fail_json(msg=repr(e))
    module.exit_json(**result)



def main():
    run_module()


if __name__ == "__main__":
    main()

