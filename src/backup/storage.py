import os

class Storage:
    """
    Stores the backup data
    """
    def __init__(self, config, all_folders, folder_hierarchy):
        self._config = config
        self._all_folders = all_folders
        self._hierarchy = folder_hierarchy
        
    def output_folders(self):
        """
        Outputs the folder hierarchy
        """
        self._output_hierarchy(self._hierarchy, '')
    
    def _output_hierarchy(self, curr_hierarchy, parent_path):
        """
        Recursive function to output the hierarchy
        """
        # output the current node
        for curr_node in curr_hierarchy.iterkeys():
            curr_path = parent_path + os.path.sep + self._all_items[curr_node][u'name']
            print curr_path
            self._output_hierarchy(curr_hierarchy[curr_node], curr_path)
