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


Requirement
===========

* z/OS
  * FTPD is running on the z/OS
* Ansible 2.9 or above
  * Python 3


Installation
============

Install the IBM z/OS core FTP collection in your environment.


```bash
ansible-galaxy collection install ibm-ibm_zos_core_ftp-1.0.0.tar.gz
```


Next, set your FTP login information to the environment variables.


```bash
export FTP_USERID=ftp_userid
export FTP_PASSWORD=ftp_password
export FTP_HOST=ftp_hostname
```


Usage
=====

Create a playbook file as below.


site.yml
```yml
---
- hosts: localhost
  collections: 
    - ibm.ibm_zos_core_ftp

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

```


Then, execute the playbook.


```bash
ansible-playbook site.yml
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
