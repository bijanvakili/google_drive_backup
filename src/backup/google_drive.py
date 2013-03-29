
class GoogleDriveDownload:
    _MIME_TYPE_FOLDER = u'application/vnd.google-apps.folder'
    _ITEMS_PER_DOWNLOAD = 15
    
    """
    Manager to download a hierarchy of files from Google Drive
    
    Returns a tuple containing:
        all_folders - list of folder meta information
        folder_hierarchy - dict of dicts describing folder hierarchy (index by 'id')
    """
    def __init__(self, config, drive_service):
        self._config = config['backup']
        self._drive_service = drive_service
        
    def get_folder_hierarchy(self):
        """
        Downlaods and constructs the folder hierarchy as a dictionary
        """
        
        # retrieve the flat list of all folders and filter for only
        # the salient hierarchical link information
        all_folders = {}
        keep_downloading = True
        page_token = None
        while keep_downloading:
            query_params = { 
                            'q' : "trashed = %s and mimeType = '%s'" % 
                                (self._config['include_trashed'], self._MIME_TYPE_FOLDER),
                            'maxResults' : self._ITEMS_PER_DOWNLOAD}
            if page_token:
                query_params['pageToken'] = page_token
            current_drive_results = self._drive_service.files().list(**query_params).execute()
            page_token = current_drive_results.get('nextPageToken')
            
            for item in current_drive_results[u'items']:
                # NOTE: we only care about the first parent 
                parent = item['parents'][0]
                all_folders[ item[u'id'] ] = { u'name' : item[u'title'], 
                    u'id' : item[u'id'], u'parent' : None if parent[u'isRoot'] else parent[u'id']}
                
            if not page_token:
                keep_downloading = False
    
        # construct the hierarchy
        folder_hierarchy = {}
        for folder in all_folders.itervalues():
            
            parent_path = [folder[u'id']]
            curr_parent_id = folder[u'parent']
            while curr_parent_id:
                parent_path.insert( 0, curr_parent_id)
                curr_parent_id = all_folders[curr_parent_id][u'parent']
            
            curr_hierarchy = folder_hierarchy
            for curr_parent_id in parent_path:
                if curr_parent_id not in curr_hierarchy:
                    curr_hierarchy[curr_parent_id] = {}
                curr_hierarchy = curr_hierarchy[curr_parent_id]
    
        return (all_folders, folder_hierarchy)
