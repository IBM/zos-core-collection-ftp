Ansible Collection - ibm.ibm_zos_core_ftp
=========================================

This is a collection that provides some of the functionality of the [IBM z/OS core collection](https://galaxy.ansible.com/ibm/ibm_zos_core) via FTP, and was developed to make Ansible available to customers who do not meet the prerequisites for the IBM z/OS core collection.

It is designed to make it easy to migrate from this collection to the original one when you are ready to use it. You can use the same module names and parameter names, and expect the same return values.


Features
========

You can use the following modules. For guides and reference, please review the [documentation](https://ibm.github.io/z_ansible_collections_doc/ibm_zos_core/docs/source/modules.html).


* zos_job_submit
* zos_operator
* zos_tso_command
* zos_job_output


You can also use FTPS (FTP over SSL/TLS) to settle the FTP security issue.


Requirement
===========

* z/OS
  * FTPD is running on the z/OS
  * A userid with access to JESSPOOL resources for SDSF

* Ansible 2.9 or above
  * Python 3


Installation
============

Install the IBM z/OS core FTP collection in your environment.


```bash
git clone https://github.com/IBM/zos-core-collection-ftp.git
cd zos-core-collection-ftp
ansible-galaxy collection build
ansible-galaxy collection install daiki_shimizu-ibm_zos_core_ftp-1.0.0.tar.gz
```


Next, set your FTP login information and job class parameters to the environment variables.


```bash
export FTP_USERID=ftp_userid
export FTP_PASSWORD=ftp_password
export FTP_HOST=ftp_hostname
export FTP_PORT=ftp_port
export FTP_JOB_CLASS=job_class
export FTP_JOB_MSGCLASS=job_msgclass
```



Finally, give access to the JESSPOOL resources to the userid.

* If SAF is disabled, define the userid as a member of ISFSPROG group in ISFPRMxx.
* If SAF is enabled, define one of the following resource profiles of the SDSF class and grant access to the profile to the userid.


To grant access to GROUP.ISFSPROG.SDSF resource profile.


```
RDEFINE SDSF GROUP.ISFSPROG.SDSF UACC(NONE)
PERMIT GROUP.ISFSPROG.SDSF CLASS(SDSF) ID(userid) ACCESS(READ)
SETROPTS RACLIST(SDSF) REFRESH
```


To grant access to ISF\*.\*\* resource profile.


```
RDEFINE SDSF ISF*.** UACC(NONE)
PERMIT ISF*.** CLASS(SDSF) ID(userid) ACCESS(ALTER)
SETROPTS RACLIST(SDSF) REFRESH
```


Usage
=====

Create a playbook file as below.


site.yml
```yml
---
- hosts: localhost
  collections: 
    - daiki_shimizu.ibm_zos_core_ftp

  tasks:
    - name: Submit a JCL on z/OS Dataset
      zos_job_submit:
        src: DAIKI.ANSIBLE.PDS(BR14CRE)
        location: DATA_SET

    - name: Submit a local JCL
      zos_job_submit:
        src: /tmp/BR14CR1
        location: LOCAL

    - name: Execute an operator command
      zos_operator:
        cmd: "D U,DASD,ONLINE"

    - name: Execute a TSO command
      zos_tso_command:
        commands:
          - "LU DAIKI"
    - name: Display a job output
      zos_job_output:
        job_id: "JOB08047"

```


Then, execute the playbook.


```bash
ansible-playbook site.yml
```


How to connect z/OS via a SSH tunnel SOCKS5 proxy
================================================

This collection support SSH tunnel SOCKS5 proxy(hereafter referred to as jumphost). If you would like to connect z/OS via a jumphost like jumphosts, you should do the following additional steps.


First, install PySocks in your controller node.


```bash
pip3 install PySocks
```


Second, set the port number for SSH tunnel to FTP_SOCKS_PORT environment variable.


```bash
export FTP_SOCKS_PORT=10022
```


Finally, add a task to establish an SSH tunnel in the beginning of the tasks in the playbook. According to your environemt, set the username and IP address of the jumphost to jumphost_ssh_user and jumphost_ip_address. And set the ssh private key required to connect the jumphost to JUMPHOST_SSH_PRIVATE_KEY. The port number (10022) specified here must match that of FTP_SOCKS_PORT above.


```bash
  tasks:
    - shell: |
        bash -c '/usr/bin/ssh -CfNq -D 127.0.0.1:10022 {{ jumphost_ssh_user }}@{{ jumphost_ip_address }} -i $JUMPHOST_SSH_PRIVATE_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ;sleep 30'
```


How to establish FTPS secure connection
======
Currently, you can use TLS 1.2. To establish FTPS secure connection, you have to set 1.2 to FTP_TLS_VERSION environment variable and the path of the FTPS certificate to FTP_TLS_CERT_FILE environment variable.


```bash
export FTP_USERID=ftp_userid
export FTP_PASSWORD=ftp_password
export FTP_HOST=ftp_hostname
export FTP_PORT=ftps_port
export FTP_JOB_CLASS=job_class
export FTP_JOB_MSGCLASS=job_msgclass
export FTP_TLS_VERSION=1.2
export FTP_TLS_CERT_FILE=certificate.pem
```


When you don't use FTPS, delete the definition of the FTP_TLS_VERSION environment variable.


```bash
unst FTP_TLS_VERSION
```


Author
======

* Daiki Shimizu
* IBM Japan
* dshimizu@jp.ibm.com


Copyright
=========

IBM Corporation 2021.


License
=======

[Apache License Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).
