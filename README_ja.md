Ansible Collection - ibm.ibm_zos_core_ftp
=========================================

これは、FTP経由で[IBM z/OS core collection](https://galaxy.ansible.com/ibm/ibm_zos_core)の機能の一部を提供するcollectionです。IBM z/OS core collectionの前提条件を満たしていないお客様でもAnsibleを利用できるように開発されました。


IBM z/OS core collectionが使えるようになったら、このcollectionから元のIBM z/OS core collectionへ簡単に移行できるように設計されています。同じモジュール名やパラメータ名を使用し、同じ戻り値を期待することができます。


機能
========

以下のモジュールを利用することができます。詳しいガイドは、[マニュアル](https://ibm.github.io/z_ansible_collections_doc/ibm_zos_core/docs/source/modules.html)をご覧ください。


* zos_job_submit
* zos_operator
* zos_tso_command


前提
===========

* z/OS
  * FTPDがz/OS上で動いていること
  * JESSPOOLリソースにアクセスできるユーザーID
* Ansible 2.9 or above
  * Python 3


導入
============

IBM z/OS core FTP collectionをお使いの環境に導入します。


```bash
git clone https://github.com/IBM/zos-core-collection-ftp.git
cd zos-core-collection-ftp
ansible-galaxy collection build
ansible-galaxy collection install ibm-ibm_zos_core_ftp-1.0.0.tar.gz
```

次に、FTPのログイン情報とジョブのパラメータを環境変数に設定します。


```bash
export FTP_USERID=ftp_userid
export FTP_PASSWORD=ftp_password
export FTP_HOST=ftp_hostname
export FTP_PORT=ftp_port
export FTP_JOB_CLASS=job_class
export FTP_JOB_MSGCLASS=job_msgclass
```


最後に、JESSPOOLリソースへのアクセスを許可します。

* SAFが無効の場合は、ISFPRMxxのISFSPROGグループのメンバーとしてユーザーIDを定義します。
* SAFが有効な場合、SDSFクラスの以下のリソースプロファイルのいずれかを定義し、そのプロファイルへのアクセスをユーザーIDに許可します。


GROUP.ISFSPROG.SDSFリソースプロファイルへのアクセスを許可するには、次のようにします。


```
RDEFINE SDSF GROUP.ISFSPROG.SDSF UACC(NONE)
PERMIT GROUP.ISFSPROG.SDSF CLASS(SDSF) ID(userid) ACCESS(READ)
SETROPTS RACLIST(SDSF) REFRESH
```


ISF\*.\*\*リソースプロファイルへのアクセスを許可するには、次のようにします。


```
RDEFINE SDSF ISF*.** UACC(NONE)
PERMIT ISF*.** CLASS(SDSF) ID(userid) ACCESS(ALTER)
SETROPTS RACLIST(SDSF) REFRESH
```


使い方
=====

以下のようなplaybookを作成します。


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


そして、playbookを実行します。


```bash
ansible-playbook site.yml
```


開発者
======

* Daiki Shimizu
* IBM Japan
* dshimizu@jp.ibm.com


著作権
=========

IBM Corporation 2021.


ライセンス
=======

[Apache License Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).
