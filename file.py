import os
from enum import Enum
import hashlib
import shutil

class Filetype(Enum):
    """
        Enumeration of different filetypes
    """
    FILETYPE_FILE = 'FILE'
    FILETYPE_DIR = 'DIR'
    FILETYPE_SYMLINK = 'SYMLINK'

class File:
    def __init__(self, filepath: str, basepath: str, filetype=Filetype.FILETYPE_FILE, digest=None):
        self._filetype = filetype
        self._relpath = os.path.relpath(filepath, basepath) # Path relative to the basepath
        self._basepath = basepath
        self._filepath = filepath
        self._md5 = self.digest().decode() if digest is None else digest

    def get_filepath(self): return self._filepath
    def get_relpath(self): return self._relpath
    def get_filetype(self): return self._filetype

    def digest(self):
        """Calculate the MD5 digest of the file"""
        if self._filetype == Filetype.FILETYPE_DIR:
            return self._dir_digest(self._filepath)
        else:
            return self._file_digest(self._filepath)

    def _dir_digest(self, dirpath):
        """Calculate the MD5 digest of the directory"""
        # Add the directory name to enforce hash changes on directory name change
        md5_hash = hashlib.md5(os.path.basename(dirpath).encode('utf-8'))

        for entry in sorted(os.listdir(dirpath)):
            path = os.path.join(dirpath, entry)

            if os.path.isdir(path):
                md5_hash.update( self._dir_digest(path) )
            else:
                md5_hash.update( self._file_digest(path) )

        return md5_hash.hexdigest().encode('utf-8')

    def _file_digest(self, filepath):
        """Calculate the MD5 digest of the file"""
        # Add the file name to enforce hash changes on file name change
        _hash = hashlib.md5(os.path.basename(filepath).encode('utf-8'))

        with open(filepath, 'rb') as file:
            _hash.update(file.read())

        return _hash.hexdigest().encode('utf8')

    def exists(self):
        """Check if file exists"""
        return os.path.exists(self._filepath)

    def copy_to_dir(self, dirpath):
        """Copy file to a directory"""
        if self._filetype == Filetype.FILETYPE_DIR:
            shutil.copytree(self._filepath, os.path.join(dirpath, os.path.basename(self._filepath)))
        else:
            shutil.copy(self._filepath, dirpath)

    def to_dict(self):
        """Serialize file"""
        return {
            'relpath': self._relpath,
            'filetype': self._filetype.value,
            'md5': self._md5
        }
