import os
import zipfile
import shutil
import tempfile
from enum import Enum
from file import File, Filetype
from backup_managers.manager_local import ManagerLocal
from backup_managers.manager_drive import ManagerDrive
from backup_managers.abstract_manager import AbstractManager
from utils import ask_for_confirmation

class ManagerType(Enum):
    LOCAL = 'LOCAL'
    DRIVE = 'DRIVE'

class BackupManager():
    def __init__(self, group, manager_type: ManagerType):
        self.group = group

        self._manager: AbstractManager = self.build_manager_from_type(manager_type)

    def build_manager_from_type(self, manager_type: ManagerType) -> AbstractManager:
        group_name = 'NO_GROUP' if self.group is None else self.group.get_name()

        if manager_type == ManagerType.LOCAL:
            return ManagerLocal(group_name)
        elif manager_type == ManagerType.DRIVE:
            return ManagerDrive(group_name)
        else:
            raise ValueError('Incorrect manager type: ' + manager_type.value)

    def _check_files(self):
        """
            Check if all the files in the group exist. Ask for confirmation if not
            Returns True if all files exists or the user has decided to continue
            Returns False if the user has decided to not continue
        """
        self.group.log('...Seeing if all files exist')

        # Return false if the confirmation is negative for any file
        for file in self.group.get_files():
            if not file.exists():
                question = f"File {file.get_filepath()} doesn't exist. Continue?"
                if ask_for_confirmation(question) is False:
                    return False

        return True

    def _zip_files(self, zip_path):
        """Zip all the files in a group"""
        self.group.log('...Zipping files')

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in self.group.get_files():
                #Skip file if it doesn't exist, since it should have asked for confirmation before
                if file.exists():
                    if file.get_filetype() == Filetype.FILETYPE_DIR:
                        paths = []
                        for root, dirs, file_list in os.walk(file.get_filepath()):
                            paths += [ os.path.join(root, d) for d in dirs ]
                            paths += [ os.path.join(root, f) for f in file_list ]

                        for path in paths:
                            zipf.write(path, arcname=os.path.relpath(path, self.group.get_basepath()))
                    else:
                        zipf.write(file.get_filepath(), arcname=file.get_relpath())

    def backup(self, rotation_number: int):
        self.group.log('...Creating backup')

        temp_dir = tempfile.TemporaryDirectory()
        zip_path = os.path.join(temp_dir.name, self.group.get_name() + '.zip')

        # If all files exists or the user has decided to continue anyways
        if self._check_files():
            self._zip_files(zip_path)

            self._manager.create_dir()
            self._manager.rotate_files(rotation_number)
            self._manager.move_zip(zip_path)

    def clean_backups(self):
        self.group.log('...Cleaning backups')
        self._manager.clean_backups()

    def list_backups(self):
        self._manager.list_backups()

    def get_latest_backup(self, target_dir):
        self.group.log(f'...Getting latest backup to {target_dir}')
        self._manager.copy_latest_backup(target_dir)

    def get_all_backups(self, target_dir):
        group_dir = os.path.join(target_dir, self.group.get_name())
        self.group.log(f'...Copying to {group_dir}')

        os.makedirs(group_dir, exist_ok=True)
        self._manager.copy_all_backups(group_dir)

    def _extract_zip(self, target_dir, filename):
        self.group.log('...Extracting zip')
        with zipfile.ZipFile(os.path.join(target_dir, filename), 'r') as zipf:
            zipf.extractall(target_dir)

    def _digest_coincides(self, target_dir):
        """Check if the digest for all the files present in target_dir coincide"""
        for file in self.group.get_files():
            filepath_in_temp = os.path.join(target_dir, file.get_relpath())

            if os.path.exists(filepath_in_temp):
                filetype = Filetype.FILETYPE_DIR if os.path.isdir(filepath_in_temp) else Filetype.FILETYPE_FILE
                previous_digest = file.get_digest()
                actual_digest = File(filepath_in_temp, target_dir, filetype=filetype).digest().decode('utf-8')

                if previous_digest != actual_digest:
                    self.group.log(f'Digest check failed: {file.get_relpath()} {previous_digest} != {actual_digest}')
                    return False

        return True

    def restore(self):
        # First uncompress in a temporary folder in case there is any error
        temp_dir = tempfile.TemporaryDirectory()

        self.get_latest_backup(temp_dir.name)
        self._extract_zip(temp_dir.name, 'backup.zip')

        if self._digest_coincides(temp_dir.name):
            # Move files to be replaced to a temporary directory just in case
            replaced_files_dir = os.path.join(tempfile.gettempdir(), 'replaced_files')
            os.makedirs(replaced_files_dir, exist_ok=True)

            self.group.log('...Copying files from temp')
            for file in self.group.get_files():
                filepath_in_temp = os.path.join(temp_dir.name, file.get_relpath())
                filepath_in_replaced_files_dir = os.path.join(replaced_files_dir, file.get_relpath())

                if os.path.exists(filepath_in_temp):
                    if file.exists():
                        # Move file to temporary dir
                        shutil.move(file.get_filepath(), filepath_in_replaced_files_dir)

                    # Move extracted file to original path
                    shutil.move(filepath_in_temp, file.get_filepath())
                    self.group.log(f'...Restored {file.get_relpath()}')

            self.group.log(f'...Previous files moved to {replaced_files_dir}')
        else:
            raise ValueError('Couldn\'t restore files: Digest doesn\'t match.')
