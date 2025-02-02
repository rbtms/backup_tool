#!/usr/bin/scripts/backup/.venv/bin/python
import argparse
from config import Config
from backup_manager import BackupManager
from backup_managers.backup_drive import get_remote_file, upload_remote_file, delete_remote_file

def get_parser():
    """
        Argument parser
            list
            add <group name> <basepath>
            remove <group name>
            addfile <group name> <relative filepath>
            removefile <group name> <relative filepath>
            setproperty <group name> <attribute name> <attribute value>
            backup <group name>
            get <group name> <target directory>
            getall
            restore <group name>
    """
    parser = argparse.ArgumentParser(description="Backup utilities")
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="List all groups")

    # group add
    add_group_parser = subparsers.add_parser("add", help="Add a new group")
    add_group_parser.add_argument("group_name", type=str, help="Name of the group to add")
    add_group_parser.add_argument("group_basepath", type=str, help="Basepath of the group to add")

    # group remove
    remove_group_parser = subparsers.add_parser("remove", help="Remove a group")
    remove_group_parser.add_argument("group_name", type=str, help="Name of the group to remove")

    # group addfile
    addfile_parser = subparsers.add_parser("addfile", aliases=['fileadd'], help="Add a file to a group")
    addfile_parser.add_argument("group_name", type=str, help="Name of the group to add the file to")
    addfile_parser.add_argument("filename", type=str, help="Filepath")

    # group removefile
    removefile_parser = subparsers.add_parser("removefile", aliases=['fileremove'], help="Remove a file from a group")
    removefile_parser.add_argument("group_name", type=str, help="Name of the group to remove the file from")
    removefile_parser.add_argument("filename", type=str, help="Relative filepath")

    # group set
    add_group_parser = subparsers.add_parser("setproperty", help="Set a group property")
    add_group_parser.add_argument("group_name", type=str, help="Name of the group")
    add_group_parser.add_argument("group_property", type=str, help="Name of the property")
    add_group_parser.add_argument("group_property_value", type=str, help="New value")

    # group backup
    backup_group_parser = subparsers.add_parser("save", help="Backup a group")
    backup_group_parser.add_argument("group_name", type=str, help="Name of the group to backup")

    # group get
    get_group_backup_parser = subparsers.add_parser("get", help="Copy the latest backup a group to a directory")
    get_group_backup_parser.add_argument("group_name", type=str, help="Name of the group")
    get_group_backup_parser.add_argument("target_dir", type=str, help="Target directory")

    get_all_parser = subparsers.add_parser('getall', help="Copy all the files to a directory")
    get_all_parser.add_argument("target_dir", type=str, help="Target directory")

    # group restore
    backup_group_parser = subparsers.add_parser("restore", help="Restore a group backup")
    backup_group_parser.add_argument("group_name", type=str, help="Name of the group to restore")

    # remote get
    remote_get_parser = subparsers.add_parser('remoteget', help='Get a remote file')
    remote_get_parser.add_argument("file_id", type=str, help="Id of the file")
    remote_get_parser.add_argument("target_dir", type=str, help="Target directory")

    # remote upload
    remote_remove_parser = subparsers.add_parser('remoteupload', help='Upload a file to remote')
    remote_remove_parser.add_argument("filename", type=str, help="Filename")

    # remote remove
    remote_remove_parser = subparsers.add_parser('remotedel', help='Remove a remote file')
    remote_remove_parser.add_argument("file_id", type=str, help="Id of the file")

    return parser

def get_group(group_name, config):
    """Find a group raising an error on failure"""
    group = config.find_group_with_name(group_name)

    if group is None:
        raise ValueError('FileGroup with name "' + group_name + '" doesn\'t exist')
    else:
        return group

def add_group(group_name, group_basepath, config):
    """
        Add a new group
    """
    config.add_group(group_name, group_basepath)

def remove_group(group_name, config):
    group = get_group(group_name, config)
    group.clean_backups()
    config.remove_group_with_name(group_name)

def add_file(group_name, filename, config):
    """
        Add a file to a group
    """
    group = get_group(group_name, config)
    group.add_file_with_path(filename)

def remove_file(group_name, filename, config):
    """
        Remove a file from a group
    """
    group = get_group(group_name, config)
    group.remove_file_with_relpath(filename)

def set_group_property(group_name, property_name, property_value, config):
    """
        Modify a group property
    """
    group = get_group(group_name, config)
    group.set_property(property_name, property_value)

def backup_group(group_name, config):
    """
        Backup the files of a group
    """
    group = get_group(group_name, config)
    group.backup(config.rotation_number)

def get_backup(group_name, target_dir, config):
    """
        Get the latest backup of a group
    """
    group = get_group(group_name, config)
    group.get_latest_backup(target_dir)

def get_all_backups(target_dir, config):
    for group in config.groups:
        group.get_all_backups(target_dir)

def list_current_backups(manager_type):
    BackupManager(None, manager_type).list_backups()

def restore_group(group_name, config):
    """
        Restore the files of a group
    """
    group = get_group(group_name, config)

    group.restore()

def main():
    parser = get_parser()
    args = parser.parse_args()

    config = Config()
    config.load()

    if args.command is None:
        print()
        print(config)
    elif args.command == 'list':
        list_current_backups(config.manager_type)
    elif args.command == 'add':
        add_group(args.group_name, args.group_basepath, config)
        config.save()
    elif args.command == 'remove':
        remove_group(args.group_name, config)
        config.save()
    elif args.command == 'addfile':
        add_file(args.group_name, args.filename, config)
        config.save()
    elif args.command == 'removefile':
        remove_file(args.group_name, args.filename, config)
        config.save()
    elif args.command == 'setproperty':
        set_group_property(args.group_name, args.group_property, args.group_property_value, config)
        config.save()
    elif args.command == 'get':
        get_backup(args.group_name, args.target_dir, config)
    elif args.command == 'getall':
        get_all_backups(args.target_dir, config)
    elif args.command == 'save':
        backup_group(args.group_name, config)
    elif args.command == 'restore':
        restore_group(args.group_name, config)
    elif args.command == 'remoteget':
        get_remote_file(args.file_id, args.target_dir)
    elif args.command == 'remoteupload':
        upload_remote_file(args.filename)
    elif args.command == 'remotedel':
        delete_remote_file(args.file_id)
    else:
        raise ValueError('Invalid command: ' + args.command)

main()
