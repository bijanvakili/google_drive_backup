from datetime import datetime
import time
import logging
import os

class DownloadError(Exception):
    """
    Exception class for all download operations
    """
    def __init__(self, http_response_code, content):
        self._code = http_response_code
        self._content = content
        
    def __str__(self):
        return 'HTTP Code: {0}\n{1}'.format(self._code, self._content)
    

class GoogleDriveDownload:
    _MIME_TYPE_FOLDER = u'application/vnd.google-apps.folder'
    _ITEMS_PER_DOWNLOAD = 15
    
    """
    Manager to download a hierarchy of files from Google Drive
    
    Returns a tuple containing:
        all_folders - list of folder meta information
        folder_hierarchy - dict of dicts describing folder hierarchy (index by 'id')
    """
    def __init__(self, config, drive_service, dry_run):
        self._config = config[u'backup']
        self._drive_service = drive_service
        self._dry_run = dry_run
        self._logger = logging.getLogger('drive_backup.backup.GoogleDriveDownload')

    def iterfolder(self, folder_id):
        """
        Iterator for all files in the drive
        """
        keep_downloading = True
        page_token = None
        while keep_downloading:
            current_drive_results = self._get_file_listing_page(
                "trashed = %s and mimeType != '%s' and '%s' in parents" % 
                    (self._config[u'include_trashed'], self._MIME_TYPE_FOLDER, folder_id), 
                page_token)
            page_token = current_drive_results.get('nextPageToken')
            if not page_token:
                keep_downloading = False
            for curr_file in current_drive_results[u'items']:
                yield curr_file
    
    def get_folder_hierarchy(self):
        """
        Downloads and constructs the folder hierarchy as a dictionary
        
        Returns:
            all_folders - dictionary of folder metadata all indexed by id
            folder_hierarchy - dictionary of dictionaries describing the folder hierarchy
        """
        
        # retrieve the flat list of all folders and filter for only
        # the salient hierarchical link information
        all_folders = {}
        keep_downloading = True
        page_token = None
        while keep_downloading:
            current_drive_results = self._get_file_listing_page("trashed = %s and mimeType = '%s'" % 
                                (self._config[u'include_trashed'], self._MIME_TYPE_FOLDER), page_token)
            page_token = current_drive_results.get('nextPageToken')
            
            for item in current_drive_results[u'items']:
                # NOTE: we only care about the first parent 
                parent = item['parents'][0]
                all_folders[ item[u'id'] ] = { u'name' : item[u'title'], 
                    u'id' : item[u'id'], u'parent' : u'root' if parent[u'isRoot'] else parent[u'id']}
                
            if not page_token:
                keep_downloading = False
    
        # construct the hierarchy
        folder_hierarchy = { u'root': {} }
        for folder in all_folders.itervalues():
            
            parent_path = [folder[u'id']]
            curr_parent_id = folder[u'parent']
            while curr_parent_id != u'root':
                parent_path.insert( 0, curr_parent_id)
                curr_parent_id = all_folders[curr_parent_id][u'parent']
            
            curr_hierarchy = folder_hierarchy[u'root']
            for curr_parent_id in parent_path:
                if curr_parent_id not in curr_hierarchy:
                    curr_hierarchy[curr_parent_id] = {}
                curr_hierarchy = curr_hierarchy[curr_parent_id]
    
        all_folders[u'root'] = { u'name': 'root', u'id' : u'root', 
                                u'parent' : None }
        return (all_folders, folder_hierarchy)
    
    def get_relative_folder_path(self, folder_id, all_folders):
        """
        Returns a relative folder path
        """
        if folder_id == u'root':
            return ''
        
        folder = all_folders[folder_id]
        parent_path_components = [folder[u'name']]
        curr_parent_id = folder[u'parent']
        while curr_parent_id != u'root':
            parent_path_components.insert( 0, all_folders[curr_parent_id][u'name'])
            curr_parent_id = all_folders[curr_parent_id][u'parent']
        return os.path.sep.join(parent_path_components)
    
    def get_filename(self, file_obj):
        """
        Determines the local filename for a file object
        """
        if file_obj[u'mimeType'] in self._config[u'download_formats']:
            file_format = self._config[u'download_formats'][file_obj[u'mimeType']]
            return '{0}.{1}'.format(file_obj[u'title'], file_format['extension'])
        else:
            return file_obj[u'title']
        
    def download_file(self, file_obj, filename):
        """
        Downloads a drive file in a preferred format
        
        file_obj - File resource meta-information
        local_download_path - Local path to store the file
        """
        
        # prepare the file metadata
        modification_time = datetime.strptime(file_obj[u'modifiedDate'],
                                          '%Y-%m-%dT%H:%M:%S.%fZ')
        
        self._logger.info('Downloading [{0}]: {1}'.format(file_obj[u'modifiedDate'], filename))
        if self._dry_run:
            return

        # download the file to the local storage
        if u'exportLinks' in file_obj:
            file_format = self._config[u'download_formats'][file_obj[u'mimeType']]
            download_url = file_obj[u'exportLinks'][file_format['content_type']]
        else:
            download_url = file_obj[u'downloadUrl']
        http_response, content = self._drive_service._http.request(download_url)
        if http_response.status != 200:
            raise DownloadError(http_response.status, content)
        with open(filename, 'w') as fp:
            fp.write(content)
            
        # artificially set the local file's modification time to match Google Drive
        os.utime(filename, 
                 (time.mktime( datetime.now().timetuple() ), 
                  time.mktime( modification_time.timetuple() )))
        

    def _get_file_listing_page(self, query, page_token):
        """
        Retrieves a file listing
        
        Returns:
        file_listing - list of file resources for this page
        """
        query_params = {'q' : query, 'maxResults' : self._ITEMS_PER_DOWNLOAD}
        if page_token:
            query_params['pageToken'] = page_token
        drive_results = self._drive_service.files().list(**query_params).execute()
        return drive_results
