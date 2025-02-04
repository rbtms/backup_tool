import os
import time
from pathlib import Path
import tempfile
from datetime import datetime
import yaml
from filegroup import FileGroup
from file import Filetype
from backup_manager import ManagerType
from backup_managers.manager_drive import get_config_file_contents, update_config_file

class Config:
    DEFAULT_FILEPATH = os.path.join(os.path.expanduser('~'), '.backup_config.yaml')
    DEFAULT_ROTATION_NUMBER = 4
    DEFAULT_MANAGER_TYPE = ManagerType('LOCAL')
    TRY_TO_FETCH_REMOTE_CONFIG = True

    def __init__(self, epoch=0):
        self.time = int(time.time()) if epoch == 0 else epoch
        # Number of files to rotate (backup.zip -> backup.zip.1...)
        self.rotation_number = self.DEFAULT_ROTATION_NUMBER
        self.groups: list[FileGroup] = []
        self.manager_type: ManagerType = self.DEFAULT_MANAGER_TYPE

    def __str__(self):
        return yaml.dump(self._to_dict(), Dumper=yaml.Dumper, sort_keys=False)

    def pretty_print(self):
        ansi_blue = '\033[1;94m'
        ansi_red = '\033[1;91m'
        ansi_reset = '\033[0m'
        bottle_path = '/home/alvaro/.var/app/com.usebottles.bottles/data/bottles/bottles/'

        print()
        print(f'{ansi_blue}Time{ansi_reset}:', datetime.fromtimestamp(self.time))
        print(f'{ansi_blue}File rotations{ansi_reset}:', self.rotation_number)
        print(f'{ansi_blue}Manager Type{ansi_reset}:', self.manager_type.value)
        print()
        print(f'{ansi_blue}Groups{ansi_reset}:')

        for group in self.groups:
            # Replace some paths for ease of read
            basepath = group.get_basepath()
            basepath = basepath.replace('/home/alvaro/.var/app/com.usebottles.bottles/data/bottles/bottles/', f'{ansi_red}[BOTTLE]{ansi_reset} ')
            print(f'{" "*4}{ansi_blue}{group.get_name()}{ansi_reset} - {basepath}')

            for file in group.get_files():
                relpath = file.get_relpath()
                relpath = relpath.replace(bottle_path, '[BOTTLE]')


                if file.get_filetype() == Filetype.FILETYPE_DIR:
                    relpath = ansi_blue + relpath + ansi_reset

                print(f'{" "*8}{relpath}')

        print()

    def find_group_with_name(self, name):
        """Search for a group with a given name"""
        for group in self.groups:
            if group.get_name() == name:
                return group

        return None

    def group_with_name_exists(self, name):
        """Check if the config has a group with a given name"""
        return self.find_group_with_name(name) is not None

    def add_group(self, group_name: str, group_basepath: str):
        """Add a group to config"""
        if group_basepath.startswith('~'): # ~/file
            group_basepath = os.path.expanduser(group_basepath)
        elif not os.path.isabs(group_basepath): # ./file
            group_basepath = os.path.abspath(group_basepath)

        if self.group_with_name_exists(group_name):
            raise ValueError('Group "' + group_name + '" already exists.')
        elif not os.path.exists(group_basepath):
            raise ValueError('basepath "' + group_basepath + '"doesn\'t exist.')

        self.groups.append(FileGroup(group_name, group_basepath, None, self.manager_type))

    def remove_group_with_name(self, name: str):
        """Remove the group from config with a given name"""
        if not self.group_with_name_exists(name):
            raise ValueError('Group "' + name + '" doesn\'t exist.')

        self.groups.remove(self.find_group_with_name(name))

    def load(self):
        """Load config from remote, and a file if it fails"""
        config_yaml = None

        if self.TRY_TO_FETCH_REMOTE_CONFIG:
            try:
                config_yaml = get_config_file_contents()
            except Exception:
                ...

        # If the config doesn't exist on remote, attempt to load it on local
        if config_yaml is None:
            print('...Failed to load remote config. Attempting local')

            if Path(self.DEFAULT_FILEPATH).is_file():
                try:
                    with open(self.DEFAULT_FILEPATH, 'r', encoding='utf8') as f:
                        config_yaml = f.read()
                #
                except Exception:
                    ...

        # Load if if any of the two has resulted in success.
        # Otherwise keep going with the existing (default one)
        if config_yaml is not None:
            config = yaml.load(config_yaml, Loader=yaml.Loader)

            self.time = config['time']
            self.rotation_number = config['rotation_number']
            self.manager_type = ManagerType(config['manager_type'])
            self.groups = self._parse_groups(config['groups'], self.manager_type)
        else:
            print('...Failed to load remote and local config. Creating new one')

    def _parse_groups(self, groups_dict: dict, manager_type: ManagerType):
        """Parse groups from a dictionary"""
        groups: list[FileGroup] = []

        for group_dict in groups_dict:
            group = FileGroup.from_dict(group_dict, manager_type)
            groups.append(group)

        return groups

    def save(self):
        """Save config to a file, local or remote"""
        config_dict = self._to_dict(int(time.time()))
        config_yaml = yaml.dump(config_dict, Dumper=yaml.Dumper)

        if self.manager_type == ManagerType.LOCAL:
            with open(self.DEFAULT_FILEPATH, 'w', encoding='utf8') as file:
                file.write(config_yaml)
        elif self.manager_type == ManagerType.DRIVE:
            # Dont delete by default in case there's an error
            _, tmpfile = tempfile.mkstemp()

            with open(tmpfile, 'w', encoding='utf8') as file:
                file.write(config_yaml)

            update_config_file(tmpfile)

    def _to_dict(self, _time=None):
        return {
            'time': self.time if _time is None else _time,
            'rotation_number': self.rotation_number,
            'manager_type': self.manager_type.value,
            'groups': [ group.to_dict() for group in self.groups ]
        }
