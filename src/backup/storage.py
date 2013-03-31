import logging
import os
import shutil

class Storage:
    """
    Stores the backup data
    """
    def __init__(self, config, dry_run):
        self._config = config
        self._logger = logging.getLogger('drive_backup.backup.Storage')
        self._dry_run = dry_run
        self._root_folder = self._config[u'backup'][u'storage_path']
        self._all_folders = None
        self._hierarchy = None

        

    def _create_folder_hierarchy(self, curr_hierarchy, parent_path):
        """
        Recursive function to output the hierarchy
        """
        # output the current node
        for curr_node in curr_hierarchy.iterkeys():
            curr_path = parent_path + os.path.sep + self._all_folders[curr_node][u'name']
            if not os.path.exists(curr_path):
                self._logger.info('Creating folder {0}'.format(curr_path))
                os.mkdir(curr_path)
            self._create_folder_hierarchy(curr_hierarchy[curr_node], curr_path)

    def erase(self):
        """
        Erases everything in the storage folder
        """
        if self._dry_run:
            return
        
        if os.path.exists(self._root_folder):
            for root, dirs, files in os.walk(self._root_folder):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))            
    
    def prepare_storage(self, all_folders, folder_hierarchy):
        """
        Recreates the folder hierarchy
        """
        self._all_folders = all_folders
        self._hierarchy = folder_hierarchy

        if not os.path.exists(self._root_folder):
            os.mkdir(self._root_folder)
        self._create_folder_hierarchy(self._hierarchy[u'root'], 
                                      self._root_folder)

    def get_root_folder(self):
        """
        Returns the storage path for a drive folder
        """
        return self._root_folder
