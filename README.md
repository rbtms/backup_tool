# backup_tool
Small and simple backup utility that supports local and remote storage providers.

Right now, this tool only supports local storage and Google Drive, for which you need to
obtain a .client_secrets.json file and place it on the backup_providers folder.

The main concept of this application is to have a small utility one can use as an
open source replacement for backup and automatic replacement of small files and folders
such as dotfiles or savegames.

```
 usage: backup.py [-h]
                  {list,config,add,remove,addfile,fileadd,removefile,fileremove,setproperty,save,get,getall,saveall,restore,remoteget,remoteupload,remotedel}
                 ...

 Backup utilities

 positional arguments:
  {list,config,add,remove,addfile,fileadd,removefile,fileremove,setproperty,save,get,getall,saveall,estore,remoteget,remoteupload,remotedel}
   list                List all files
   config              Show the config file
   add                 Add a new group
   remove              Remove a group
   addfile (fileadd)   Add a file to a group
   removefile (fileremove)
                       Remove a file from a group
   setproperty         Set a group property
   save                Backup a group
   get                 Copy the latest backup a group to a directory
   getall              Copy all the files to a directory
   saveall             Backup all groups
   restore             Restore a group backup
   remoteget           Get a remote file
   remoteupload        Upload a file to remote
   remotedel           Remove a remote file

 optional arguments:
   -h, --help            show this help message and exit
```
