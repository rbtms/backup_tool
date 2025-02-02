from abc import ABC, abstractmethod

class AbstractManager(ABC):
    @abstractmethod
    def __init__(self, group_name: str):
        ...

    @abstractmethod
    def clean_backups(self):
        ...

    @abstractmethod
    def create_dir(self):
        ...

    @abstractmethod
    def rotate_files(self, rotation_number: int):
        ...

    @abstractmethod
    def move_zip(self, zip_path: str):
        ...

    @abstractmethod
    def copy_latest_backup(self, target_dir: str):
        ...

    @abstractmethod
    def copy_all_backups(self, target_dir: str):
        ...

    @abstractmethod
    def list_backups(self):
        ...
