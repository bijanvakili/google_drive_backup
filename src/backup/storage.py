from datetime import datetime
import logging
import os
import shutil

class Storage:
    """
    Stores the backup data
    """
    def __init__(self, config, all_folders, folder_hierarchy):
        self._config = config
        self._all_folders = all_folders
        self._hierarchy = folder_hierarchy
        self._root_folder = '{0}{1}{2}'.format(
            self._config['backup']['storage_path'], 
            os.path.sep, 
            datetime.now().strftime('%y-%m-%d'))
        self._logger = logging.getLogger('drive_backup.backup.Storage')
        

    def _create_folder_hierarchy(self, curr_hierarchy, parent_path):
        """
        Recursive function to output the hierarchy
        """
        # output the current node
        for curr_node in curr_hierarchy.iterkeys():
            curr_path = parent_path + os.path.sep + self._all_folders[curr_node][u'name']
            self._logger.info('Creating folder {0}'.format(curr_path))
            if not self._config['dry_run']:
                os.mkdir(curr_path)
            self._create_folder_hierarchy(curr_hierarchy[curr_node], curr_path)

    def _erase_all(self):
        """
        Erases everything in the storage folder
        """
        if not self._config['dry_run'] and os.path.exists(self._root_folder):
            shutil.rmtree(self._root_folder)
    
    def prepare_storage(self):
        """
        Recreates the folder hierarchy
        """
        if not self._config['dry_run']:
            self._erase_all()
            os.mkdir(self._root_folder)
        self._create_folder_hierarchy(self._hierarchy[u'root'], 
                                      self._root_folder)

    def get_target_subfolder(self, folder_id):
        """
        Returns the storage path for a drive folder
        """
        if folder_id == u'root':
            return self._root_folder
        
        folder = self._all_folders[folder_id]
        parent_path_components = [folder[u'name']]
        curr_parent_id = folder[u'parent']
        while curr_parent_id != u'root':
            parent_path_components.insert( 0, self._all_folders[curr_parent_id][u'name'])
            curr_parent_id = self._all_folders[curr_parent_id][u'parent']
        parent_path_components.insert( 0, self._root_folder)
        return os.path.sep.join(parent_path_components)
