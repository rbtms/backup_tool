import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    filename=os.path.join(os.path.dirname(__file__), '.client_secrets.json')
)

class DriveFile:
    def __init__(self, file_dict, service):
        self.id = file_dict['id']
        self.name = file_dict['name']
        self.mime_type = file_dict['mimeType']
        self.is_dir = 'folder' in self.mime_type

        self._service = service

    def delete(self):
        self._service.files().delete(fileId=self.id).execute()

    def change_name(self, new_name):
        self._service.files().update(fileId=self.id, body={'name': new_name}).execute()

    def download(self, path):
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

class BackupDrive():
    def __init__(self, name):
        self._group_backup_folder = name
        self._service = build('drive', 'v3', credentials=credentials)

    def _bytes_to_readable_amount(self, byte_n: int):
        """Convert a number of bytes to a readable string"""
        if byte_n < 1024:
            return str(byte_n) + ' Bytes'
        elif byte_n < 1024**2:
            return str(byte_n/(1024**1))[:4] + ' KB'
        elif byte_n < 1024**3:
            return str(byte_n/(1024**2))[:4] + ' MB'
        elif byte_n < 1024**4:
            return str(byte_n/(1024**3))[:4] + ' GB'
        else:
            raise ValueError('Invalid byte number:', byte_n)

    def _print_storage_quotas(self):
        quotas = self._service.about().get(fields="storageQuota").execute()

        print()
        print('Used:', self._bytes_to_readable_amount(int(quotas['storageQuota']['usage'])))
        print('Left:', self._bytes_to_readable_amount(int(quotas['storageQuota']['limit'])))

    def _get_root_files(self):
        """Get the files in the root folder"""
        return [ DriveFile(file, self._service)
                for file in self._service.files().list(q=f"parents = 'root'").execute()['files'] ]

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
        dir_id = self._get_directory_id(dir_name)

        if dir_id is not None:
            try:
                file_metadata = {'name': filename, 'parents': [dir_id]}
                media = MediaFileUpload(filepath, resumable=True)

                self._service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
            except HttpError as err:
                print(f"An error occurred: {err}")
        else:
            raise ValueError('Could not upload backup. Directory ' + dir_name + ' doesn\'t exist.')

    def _change_file_name(self, file_id, new_name):
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
                self._service.files().create(body=file_metadata, fields="id").execute()
            except HttpError as error:
                print(f"An error occurred: {error}")

    def rotate_files(self, rotation_number):
        base_backup_file = 'backup.zip'
        files = self._get_files_in_dir_by_name(self._group_backup_folder)

        # Remove backup.zip.4
        if any([file.name == f'{base_backup_file}.4' for file in files]):
            file = [ file for file in files if file.name == f'{base_backup_file}.4' ][0]
            file.delete()

        # backup.zip.1 -> backup.zip.2...
        for n in range(rotation_number):
            m = rotation_number - n
            if any([file.name == f'{base_backup_file}.{m-1}' for file in files]):
                file = [ file for file in files if file.name == f'{base_backup_file}.{m-1}' ][0]
                file.change_name(f'{base_backup_file}.{m}')

        # backup.zip -> backup.zip.1
        if any([file.name == base_backup_file for file in files]):
            file = [ file for file in files if file.name == base_backup_file ][0]
            file.change_name(f'{base_backup_file}.1')

    def move_zip(self, zip_path):
        self._upload_file(zip_path, self._group_backup_folder, 'backup.zip')

    def list_backups(self, files=None, indent=0):
        if files is None: files = self._get_root_files()

        for file in files:
            print(f"{' '*indent} {file.name}\t\t\t - {file.id}")

            if file.is_dir:
                self.list_backups(file.get_folder_files(), indent+4)

        if indent == 0:
            self._print_storage_quotas()

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

def get_remote_file(file_id, target_dir):
    service = build('drive', 'v3', credentials=credentials)
    file = DriveFile({'id': file_id, 'name': '', 'mimeType': ''}, service)
    file.download(os.path.join(target_dir, 'backup.zip'))

def delete_remote_file(file_id):
    service = build('drive', 'v3', credentials=credentials)
    file = DriveFile({'id': file_id, 'name': '', 'mimeType': ''}, service)
    file.delete()
