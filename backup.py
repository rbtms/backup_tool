#!/usr/bin/scripts/backup/.venv/bin/python
import argparse
from config import Config
from filegroup import FileGroup
from backup_manager import BackupManager, ManagerType
from backup_managers.manager_drive import get_remote_file, upload_remote_file, delete_remote_file
from utils import ask_for_confirmation

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
            saveall
            restore <group name>
            remoteget <file id> <target directory>
            remoteupload <filepath>
            remoteremove <file id>
    """
    parser = argparse.ArgumentParser(description="Backup utilities")
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="List all files")

    # config
    subparsers.add_parser("config", help="Show the config file")

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
    setproperty_parser = subparsers.add_parser("setproperty", help="Set a group property")
    setproperty_parser.add_argument("group_name", type=str, help="Name of the group")
    setproperty_parser.add_argument("group_property", type=str, help="Name of the property")
    setproperty_parser.add_argument("group_property_value", type=str, help="New value")

    # save
    backup_group_parser = subparsers.add_parser("save", help="Backup a group")
    backup_group_parser.add_argument("group_name", type=str, help="Name of the group to backup")
    # --force
    backup_group_parser.add_argument('--force', action='store_true', help='Force the backup')

    # get
    get_group_backup_parser = subparsers.add_parser("get", help="Copy the latest backup a group to a directory")
    get_group_backup_parser.add_argument("group_name", type=str, help="Name of the group")
    get_group_backup_parser.add_argument("target_dir", type=str, help="Target directory")

    # getall
    get_all_parser = subparsers.add_parser('getall', help="Copy all the files to a directory")
    get_all_parser.add_argument("target_dir", type=str, help="Target directory")

    # saveall
    get_all_parser = subparsers.add_parser('saveall', help="Backup all groups")

    # group restore
    restore_group_parser = subparsers.add_parser("restore", help="Restore a group backup")
    restore_group_parser.add_argument("group_name", type=str, help="Name of the group to restore")

    # remote get
    remote_get_parser = subparsers.add_parser('remoteget', help='Get a remote file')
    remote_get_parser.add_argument("file_id", type=str, help="Id of the file")
    remote_get_parser.add_argument("target_dir", type=str, help="Target directory")

    # remote upload
    remote_upload_parser = subparsers.add_parser('remoteupload', help='Upload a file to remote')
    remote_upload_parser.add_argument("filename", type=str, help="Filename")

    # remote remove
    remote_remove_parser = subparsers.add_parser('remotedel', help='Remove a remote file')
    remote_remove_parser.add_argument("file_id", type=str, help="Id of the file")

    return parser

def get_group(group_name, config: Config) -> FileGroup:
    """Find a group raising an error on failure"""
    group = config.find_group_with_name(group_name)

    if group is None:
        raise ValueError('FileGroup with name "' + group_name + '" doesn\'t exist')
    else:
        return group

def add_group(group_name, group_basepath, config: Config):
    """
        Add a new group
    """
    config.add_group(group_name, group_basepath)

def remove_group(group_name, config: Config):
    if ask_for_confirmation(f'Are you sure you want to remove {group_name}?'):
        group = get_group(group_name, config)
        group.clean_backups()
        config.remove_group_with_name(group_name)

def add_file(group_name, filename, config: Config):
    """
        Add a file to a group
    """
    group = get_group(group_name, config)
    group.add_file_with_path(filename)

def remove_file(group_name, filename, config: Config):
    """
        Remove a file from a group
    """
    group = get_group(group_name, config)
    group.remove_file_with_relpath(filename)

def set_group_property(group_name, property_name, property_value, config: Config):
    """
        Modify a group property
    """
    group = get_group(group_name, config)
    group.set_property(property_name, property_value)

def backup_group(group_name, config: Config, force_if_unchanged=False):
    """
        Backup the files of a group
    """
    group = get_group(group_name, config)
    group.backup(config.get_rotation_number(), force_if_unchanged=force_if_unchanged)

def backup_all_groups(config: Config):
    for group in config.get_groups():
        print()
        group.backup(config.get_rotation_number(), force_if_unchanged=False)

def get_backup(group_name, target_dir, config: Config):
    """
        Get the latest backup of a group
    """
    group = get_group(group_name, config)
    group.get_latest_backup(target_dir)

def get_all_backups(target_dir, config: Config):
    for group in config.get_groups():
        print()
        group.get_all_backups(target_dir)

def list_current_backups(manager_type: ManagerType):
    BackupManager(None, manager_type).list_backups()

def restore_group(group_name, config: Config):
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

    start_config = str(config)

    if args.command is None:
        config.pretty_print()
    elif args.command == 'config':
        print()
        print(config)
    elif args.command == 'list':
        list_current_backups(config.get_manager_type())
    elif args.command == 'add':
        add_group(args.group_name, args.group_basepath, config)
    elif args.command == 'remove':
        remove_group(args.group_name, config)
    elif args.command == 'addfile':
        add_file(args.group_name, args.filename, config)
    elif args.command == 'removefile':
        remove_file(args.group_name, args.filename, config)
    elif args.command == 'setproperty':
        set_group_property(args.group_name, args.group_property, args.group_property_value, config)
    elif args.command == 'get':
        get_backup(args.group_name, args.target_dir, config)
    elif args.command == 'getall':
        get_all_backups(args.target_dir, config)
    elif args.command == 'save':
        backup_group(args.group_name, config, force_if_unchanged=args.force)
    elif args.command == 'saveall':
        backup_all_groups(config)
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

    # Detect changes on config
    if start_config != str(config):
        config.save()

main()
