import os
import hashlib
from file import File, Filetype
from backup_manager import BackupManager, ManagerType

class FileGroup:
    def __init__(self, name='unnamed_group', basepath='', digest=None, manager_type: ManagerType = None):
        if basepath is None or basepath == '':
            raise ValueError('basepath can\'t be empty.')
        elif manager_type is None:
            raise ValueError('manager_type can\'t be None.')
        elif not os.path.exists(basepath):
            raise ValueError('basepath "' + basepath + '"doesn\'t exist.')

        self._name = name
        self._basepath = basepath
        self._files: list[File] = []
        self._md5 = self.digest() if digest is None else digest

    def get_name(self): return self._name
    def get_basepath(self): return self._basepath
    def get_files(self): return self._files
    def get_md5(self): return self._md5

    def _find_file_with_path(self, filepath):
        for file in self._files:
            if file.get_filepath() == filepath:
                return file

        return None

    def set_property(self, name, value):
        """Modify property of a file group. Used exclusively from the command line."""
        if name in self.__dict__:
            self.__dict__[name] = value
        elif f'_{name}' in self.__dict__: # Private member
            self.__dict__[f'_{name}'] = value
        else:
            raise ValueError('Group ' + self._name + ' doesn\'t have property ' + name + '.')

    def digest(self):
        """MD5 hash of its files"""
        md5_hash = hashlib.md5()

        for file in self._files:
            md5_hash.update(file.digest())

        return md5_hash.hexdigest()

    def _get_filetype(self, filepath: str):
        if os.path.isdir(filepath):
            return Filetype.FILETYPE_DIR
        elif os.path.islink(filepath):
            return Filetype.FILETYPE_SYMLINK
        elif os.path.isfile(filepath):
            return Filetype.FILETYPE_FILE
        else:
            raise ValueError('Unknown filetype: ' + filepath)

    def add_file_with_path(self, filepath: str):
        if filepath.startswith('~'): # ~/file
            filepath = os.path.expanduser(filepath)
        elif not os.path.isabs(filepath): # ./file
            filepath = os.path.abspath(filepath)

        if os.path.exists(filepath):
            self._add_file(File(filepath, self._basepath, self._get_filetype(filepath)))

            # Update digest
            self._md5 = self.digest()
        else:
            raise ValueError('File "' + filepath + '" doesn\'t exist')

    def _add_file(self, file: File):
        if self._find_file_with_path(file.get_filepath()):
            raise ValueError('File "' + file.get_filepath() + '" already exists.')

        self._files.append(file)

    def remove_file_with_relpath(self, relpath):
        filepath = os.path.join(self._basepath, relpath)

        file = self._find_file_with_path(filepath)
        self._files.remove(file)

    def backup(self, rotation_number: int):
        BackupManager(self).backup(rotation_number)

    def get_latest_backup(self, target_dir):
        """Copy the latest backup to a directory"""
        BackupManager(self).get_latest(target_dir)

    def clean_backups(self):
        """Remove backups"""
        BackupManager(self).clean_backups()

    def restore(self):
        BackupManager(self).restore()

    def to_dict(self):
        return {
            'name': self._name,
            'basepath': self._basepath,
            'files': [ file.to_dict() for file in self._files ],
            'md5': self._md5
        }

    @classmethod
    def from_dict(cls, group_dict: dict, manager_type: ManagerType):
        group = cls(
            group_dict['name'],
            group_dict['basepath'],
            group_dict['md5'],
            manager_type
        )

        for file in group_dict['files']:
            group._add_file( File(
                os.path.join(group_dict['basepath'], file['relpath']),
                group_dict['basepath'],
                Filetype(file['filetype']),
                file['md5']
            ))

        return group
