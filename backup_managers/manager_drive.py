import os
import io
import tempfile
from typing import Optional
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from utils import print_directory_tree
from .abstract_manager import AbstractManager

credentials = service_account.Credentials.from_service_account_file(
    filename=os.path.join(os.path.dirname(__file__), '.client_secrets.json')
)

CONFIG_FILE_NAME = '.backup_config.yaml'
CONFIG_FILE_ROTATION = 4

class DriveFile:
    def __init__(self, file_dict, service):
        self.id = file_dict['id']
        self.name = file_dict['name']
        self.mime_type = file_dict['mimeType']
        self.is_dir = 'folder' in self.mime_type

        self._service = service

    def _log(self, msg):
        ansi_blue = '\033[1;94m'
        ansi_reset = '\033[0m'
        print(f'[{ansi_blue}{self.name}{ansi_reset} ({self.id})] {msg}')

    def delete(self):
        self._log('...Deleting')
        self._service.files().delete(fileId=self.id).execute()

    def change_name(self, new_name):
        self._log(f'...Changing name to {new_name}')
        self._service.files().update(fileId=self.id, body={'name': new_name}).execute()

    def download(self, path):
        self._log(f'...Downloading to {path}')

        try:
            request_file = self._service.files().get_media(fileId=self.id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request_file)
            done = False

            while not done:
                _, done = downloader.next_chunk()

            with open(path, 'wb') as f:
                f.write(file.getvalue())
        except HttpError as error:
            print(F'An error occurred: {error}')

    def get_folder_files(self):
        """Get files in the case it's a directory"""
        if not self.is_dir:
            raise ValueError('DriveFile ' + self.name + ' is not a directory.')
        else:
            return [ DriveFile(file, self._service)
                    for file in self._service.files().list(q=f"'{self.id}' in parents").execute()['files'] ]

class ManagerDrive(AbstractManager):
    CONFIG_FILE_NAME = '.backup_config.yaml'

    def __init__(self, name):
        self._group_backup_folder = name
        self._service = _build_service()

    def _bytes_to_readable_amount(self, byte_n: int):
        """Convert a number of bytes to a readable string"""
        if byte_n < 1024:
            return str(byte_n) + ' Bytes'
        elif byte_n < 1024**2:
            return str(round(byte_n/(1024**1), 2)) + ' KB'
        elif byte_n < 1024**3:
            return str(round(byte_n/(1024**2), 2)) + ' MB'
        elif byte_n < 1024**4:
            return str(round(byte_n/(1024**3), 2)) + ' GB'
        else:
            raise ValueError('Invalid byte number:', byte_n)

    def _print_storage_quotas(self):
        # pylint: disable=no-member
        quotas = self._service.about().get(fields="storageQuota").execute()

        print()
        print('Used:', self._bytes_to_readable_amount(int(quotas['storageQuota']['usage'])))
        print('Left:', self._bytes_to_readable_amount(int(quotas['storageQuota']['limit'])))

    def _get_root_files(self):
        # pylint: disable=no-member
        """Get the files in the root folder"""
        return [ DriveFile(file, self._service)
                for file in self._service.files().list(q="parents = 'root'").execute()['files'] ]

    def _get_files_in_dir_by_name(self, folder_name):
        """Get the files from the first dir in the root with a given name"""
        files = self._get_root_files()

        for file in files:
            if file.name == folder_name:
                return file.get_folder_files()

        return None

    def _get_directory_id(self, dir_name):
        files = self._get_root_files()

        for file in files:
            if file.is_dir and file.name == dir_name:
                return file.id

        return None

    def _upload_file(self, filepath, dir_name, filename):
        """
            Upload a file
            - filepath: File path of the file to upload
            - dir_name: Parent directory in drive. If None, it uploads it to the root
            - filename: Filename the file is to be uploaded as
        """
        print(f'[DRIVE] ...Uploading {filepath} to {dir_name}/{filename}')

        try:
            file_metadata = {'name': filename}

            # Add parent directory
            if dir_name is not None:
                dir_id = self._get_directory_id(dir_name)
                if dir_id is not None:
                    file_metadata['parents'] = [dir_id]
                else:
                    raise ValueError('Could not upload backup. Directory ' + dir_name + ' doesn\'t exist.')

            media = MediaFileUpload(filepath, resumable=True)

            # pylint: disable=no-member
            self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
        except HttpError as err:
            print(f"[DRIVE] An error occurred: {err}")

    def _change_file_name(self, file_id, new_name):
        # pylint: disable=no-member
        self._service.files().update(fileId=file_id, body={'name': new_name}).execute()

    def create_dir(self):
        # Folder doesn't exist
        if self._get_directory_id(self._group_backup_folder) is None:
            file_metadata = {
                "name": self._group_backup_folder,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": 'appDataFolder'
            }

            try:
                # pylint: disable=no-member
                self._service.files().create(body=file_metadata, fields="id").execute()
            except HttpError as error:
                print(f"An error occurred: {error}")

    def rotate_files(self, rotation_number):
        base_backup_file = 'backup.zip'
        files = self._get_files_in_dir_by_name(self._group_backup_folder)

        # Remove backup.zip.4
        file = _find_file_with_name(files, f'{base_backup_file}.4')
        if file is not None:
            file.delete()

        # backup.zip.1 -> backup.zip.2...
        for n in range(rotation_number):
            m = rotation_number - n
            file = _find_file_with_name(files, f'{base_backup_file}.{m-1}')
            if file is not None:
                file.change_name(f'{base_backup_file}.{m}')

        # backup.zip -> backup.zip.1
        file = _find_file_with_name(files, base_backup_file)
        if file is not None:
            file.change_name(f'{base_backup_file}.1')

    def move_zip(self, zip_path):
        self._upload_file(zip_path, self._group_backup_folder, 'backup.zip')

    def list_backups(self, files=None, indent=0):
        tree_dict = {}

        if files is None:
            files = self._get_root_files()

        for file in files:
            tree_dict[file.name] = { 'id': file.id, 'files': [] }

            if file.is_dir:
                _tree_dict = self.list_backups(file.get_folder_files(), indent+4)
                tree_dict[file.name]['files'] = _tree_dict

        # Print structure as a tree now that it has finished
        if indent == 0:
            print()
            print('Drive')
            print_directory_tree(tree_dict)
            self._print_storage_quotas()
            print()
        else:
            return tree_dict

    def clean_backups(self):
        for file in self._get_root_files():
            if file.is_dir and file.name == self._group_backup_folder:
                file.delete()

    def copy_latest_backup(self, target_dir):
        files = self._get_files_in_dir_by_name(self._group_backup_folder)

        if files:
            file = [ file for file in files if file.name == 'backup.zip' ][0]
            file.download(os.path.join(target_dir, 'backup.zip'))
        else:
            raise ValueError(self._group_backup_folder + ' does not have any backups.')

    def copy_all_backups(self, target_dir):
        """Copy all backups for a given group to a directory"""
        files = self._get_files_in_dir_by_name(self._group_backup_folder)

        if files is None:
            print(f'[DRIVE] ...File group {self._group_backup_folder} doesn\'t exist.')
        else:
            for file in files:
                file.download(os.path.join(target_dir, file.name))

def _build_service() -> Resource:
    return build('drive', 'v3', credentials=credentials)

def _find_file_with_name(files: list[DriveFile], name: str) -> Optional[DriveFile]:
    for file in files:
        if file.name == name:
            return file

    return None

def get_remote_file(file_id, target_dir):
    service = _build_service()

    # Get file metadata
    # pylint: disable=no-member
    file_dict = service.files().get(fileId=file_id).execute()

    file = DriveFile(file_dict, service)
    file.download(os.path.join(target_dir, file_dict['name']))

def upload_remote_file(filepath):
    manager = ManagerDrive('noname')
    manager._upload_file(filepath, None, os.path.basename(filepath))

def delete_remote_file(file_id):
    service = _build_service()
    file = DriveFile({'id': file_id, 'name': '', 'mimeType': ''}, service)
    file.delete()

def get_config_file_contents():
    temp_dir = tempfile.TemporaryDirectory()
    manager = ManagerDrive('noname')
    files = manager._get_root_files()

    if any([ file.name == CONFIG_FILE_NAME for file in files ]):
        temp_path = os.path.join(temp_dir.name, CONFIG_FILE_NAME)
        file = [ file for file in files if file.name == CONFIG_FILE_NAME ][0]
        file.download(temp_path)

        with open(temp_path, 'r', encoding='utf8') as f:
            return f.read()
    else:
        print("[DRIVE] Couldn't read remote config file.")
        return None

def update_config_file(filepath):
    manager = ManagerDrive('noname')
    files = manager._get_root_files()

    # Rotate config files

    # Remove .backup_config.yaml.4
    file = _find_file_with_name(files, f'{CONFIG_FILE_NAME}.4')
    if file is not None:
        file.delete()

    # .backup_config.yaml.1 -> .backup_config.yaml.2...
    for n in range(CONFIG_FILE_ROTATION):
        m = CONFIG_FILE_ROTATION - n
        file = _find_file_with_name(files, f'{CONFIG_FILE_NAME}.{m-1}')
        if file is not None:
            file.change_name(f'{CONFIG_FILE_NAME}.{m}')

    # .backup_config.yaml.zip -> .backup_config.yaml.1
    file = _find_file_with_name(files, CONFIG_FILE_NAME)
    if file is not None:
        file.change_name(f'{CONFIG_FILE_NAME}.1')

    # Upload file
    manager._upload_file(filepath, None, CONFIG_FILE_NAME)
