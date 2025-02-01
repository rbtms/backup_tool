import os
import zipfile
import shutil
import tempfile
from enum import Enum
from file import Filetype
from backup_local import BackupLocal
from backup_drive import BackupDrive

class ManagerType(Enum):
    LOCAL = 'LOCAL'
    DRIVE = 'DRIVE'

class BackupManager():
    def __init__(self, group, manager_type: ManagerType):
        self.group = group

        managers = { ManagerType.LOCAL: BackupLocal, ManagerType.DRIVE: BackupDrive }
        self._manager = managers[manager_type]('NO_GROUP' if group is None else self.group.get_name())

    def _ask_for_confirmation(self, question):
        """Ask a prompt to the user"""
        response = input(f'{question} (y/n) ')

        if response == 'n' or response == 'N':
            return False
        elif response == 'y' or response == 'Y':
            return True
        else:
            return self._ask_for_confirmation(question)

    def _check_files(self):
        """
            Check if all the files in the group exist. Ask for confirmation if not
            Returns True if all files exists or the user has decided to continue
            Returns False if the user has decided to not continue
        """
        print('...Seeing if all files exist')

        for file in self.group.get_files():
            if not file.exists():
                question = f"File {file.get_filepath()} doesn't exist. Continue?"
                if self._ask_for_confirmation(question) is False:
                    return False

        return True

    def _zip_files(self, zip_path):
        """Zip all the files in a group"""
        print('...Zipping files')

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
        print('...Creating backup')

        temp_dir = tempfile.TemporaryDirectory()
        zip_path = os.path.join(temp_dir.name, self.group.get_name() + '.zip')

        # If all files exists or the user has decided to continue anyways
        if self._check_files():
            self._zip_files(zip_path)

            self._manager.create_dir()
            self._manager.rotate_files(rotation_number)
            self._manager.move_zip(zip_path)

    def clean_backups(self):
        print('...Cleaning backups of ' + self.group.get_name())
        self._manager.clean_backups()

    def list_backups(self):
        self._manager.list_backups()

    def get_latest_backup(self, target_dir):
        print('...Getting latest backup')
        self._manager.copy_latest_backup(target_dir)

    def get_all_backups(self, target_dir):
        group_dir = os.path.join(target_dir, self.group.get_name())
        print(f'...Copying {self.group.get_name()} to {group_dir}')

        os.makedirs(group_dir, exist_ok=True)
        self._manager.copy_all_backups(group_dir)

    def restore(self):
        # First uncompress in a temporary folder in case there is any error
        temp_dir = tempfile.TemporaryDirectory()

        self.get_latest_backup(temp_dir.name)

        # Extract zip
        print('...Extracting zip')
        with zipfile.ZipFile(os.path.join(temp_dir.name, 'backup.zip'), 'r') as zipf:
            zipf.extractall(temp_dir.name)

        # Move files to be replaced to a temporary directory just in case
        replaced_files_dir = os.path.join(tempfile.gettempdir(), 'replaced_files')
        os.makedirs(replaced_files_dir, exist_ok=True)

        print('...Copying files')
        for file in self.group.get_files():
            filepath_in_temp = os.path.join(temp_dir.name, file.get_relpath())
            filepath_in_replaced_files_dir = os.path.join(replaced_files_dir, file.get_relpath())
            if os.path.exists(filepath_in_temp):
                if file.exists():
                    # Move file to temporary dir
                    shutil.move(file.get_filepath(), filepath_in_replaced_files_dir)
                    # Move extracted file to original path
                    shutil.move(filepath_in_temp, file.get_filepath())

        print('...Previous files moved to ' + replaced_files_dir)
