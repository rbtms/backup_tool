import os
import time
from pathlib import Path
import yaml
from filegroup import FileGroup
from backup_manager import ManagerType

class Config:
    DEFAULT_FILEPATH = os.path.join(os.path.expanduser('~'), '.backup_config_yaml')
    DEFAULT_ROTATION_NUMBER = 4
    DEFAULT_MANAGER_TYPE = ManagerType('LOCAL')

    def __init__(self, epoch=0):
        self.time = int(time.time()) if epoch == 0 else epoch
        # Number of files to rotate (backup.zip -> backup.zip.1...)
        self.rotation_number = self.DEFAULT_ROTATION_NUMBER
        self.groups: list[FileGroup] = []
        self.manager_type: ManagerType = self.DEFAULT_MANAGER_TYPE

    def __str__(self):
        return yaml.dump(self.to_dict(), Dumper=yaml.Dumper)

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

        self.groups.append(FileGroup(group_name, group_basepath))

    def remove_group_with_name(self, name: str):
        """Remove the group from config with a given name"""
        if not self.group_with_name_exists(name):
            raise ValueError('Group "' + name + '" doesn\'t exist.')

        self.groups.remove(self.find_group_with_name(name))

    def load(self, filepath=DEFAULT_FILEPATH):
        """Load config from a file"""
        if Path(filepath).is_file():
            with open(filepath, 'r', encoding='utf8') as file:
                config = yaml.load(file, Loader=yaml.Loader)

                self.time = config['time']
                self.rotation_number = config['rotation_number']
                self.manager_type = ManagerType(config['manager_type'])
                self.groups = self._parse_groups(config['groups'], self.manager_type)

    def _parse_groups(self, groups_dict: dict, manager_type: ManagerType):
        """Parse groups from a dictionary"""
        groups: list[FileGroup] = []

        for group_dict in groups_dict:
            group = FileGroup.from_dict(group_dict, manager_type)
            groups.append(group)

        return groups

    def save(self, filepath=DEFAULT_FILEPATH):
        """Save config to a file"""
        config_dict = self.to_dict(int(time.time()))
        config_yaml = yaml.dump(config_dict, Dumper=yaml.Dumper)

        with open(filepath, 'w', encoding='utf8') as file:
            file.write(config_yaml)

    def to_dict(self, t=None):
        return {
            'time': int(time.time()) if t is None else t,
            'rotation_number': self.rotation_number,
            'manager_type': self.manager_type.value,
            'groups': [ group.to_dict() for group in self.groups ]
        }
