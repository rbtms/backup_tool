import os
import shutil
import pathlib

class BackupLocal():
    BACKUP_FOLDER = '/home/alvaro/backups' # Folder where to put the backups

    def __init__(self, group_name):
        self._group_name = group_name
        self._group_backup_folder = os.path.join(self.BACKUP_FOLDER, group_name)

    def create_dir(self):
        os.makedirs(self._group_backup_folder, exist_ok=True)

    def rotate_files(self, rotation_number):
        base_backup_file = os.path.join(self._group_backup_folder, 'backup.zip') # folder/backup.zip

        for n in range(rotation_number):
            m = rotation_number - n
            if os.path.exists(f'{base_backup_file}.{m-1}'):
                # backup.zip.1 -> backup.zip.2...
                shutil.move(f'{base_backup_file}.{m-1}', f'{base_backup_file}.{m}')

        # backup.zip -> backup.zip.1
        if os.path.exists(base_backup_file):
            shutil.move(f'{base_backup_file}', f'{base_backup_file}.1')

    def move_zip(self, zip_path):
        shutil.move(zip_path, os.path.join(self._group_backup_folder, 'backup.zip'))

    def copy_latest_backup(self, target_dir):
        zip_path = os.path.join(self._group_backup_folder, 'backup.zip')

        if os.path.exists(zip_path):
            shutil.copy(zip_path, target_dir)
        else:
            print('There are no backups in ' + self._group_backup_folder + '.')

    def copy_all_backups(self, target_dir):
        """Copy all backups for a given group to a directory"""
        for file in pathlib.Path(self._group_backup_folder).iterdir():
            shutil.copy(str(file.absolute()), target_dir)

    def retrieve(self):
        ...

    def clean_backups(self):
        # Being a bit paranoid
        if self._group_backup_folder != self.BACKUP_FOLDER\
        and 'backups' in self._group_backup_folder\
        and os.path.exists(self._group_backup_folder):
            shutil.rmtree(self._group_backup_folder)

    def list_backups(self):
        os.system('tree ' + self.BACKUP_FOLDER)
