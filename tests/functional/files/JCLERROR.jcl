//SHIMIZ11 JOB CLASS=A,MSGLEVEL=(1,1),MSGCLASS=H     
//STEP1 EXEC PGM=IDCAMS,                             
//SYSPRINT DD SYSOUT=*                               
//SYSIN DD *                                         
      DEF ALIAS (NAME(ANSIBLE) RELATE(UCAT.TSOUSER)) 
/*                                                    
