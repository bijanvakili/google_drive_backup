#!/usr/bin/env python

"""
Downloads your Google drive for backup
"""

import argparse
import httplib2
import json
import logging
from logging.config import dictConfig
import os
import re
import sys
import time

from apiclient.discovery import build

from auth.credential import CredentialManager
from backup.google_drive import GoogleDriveDownload 
from backup.storage import Storage

class LevelBelowFilter(logging.Filter):
    """
    Logging filter class to include all messages below a certain level
    """
    def __init__(self, max_level):
        self.max_level = max_level
        
    def filter(self, record):
        return record.levelno <= self.max_level


class MainProgram:
    """
    Main program class
    """

    """
    Default configuration file
    """
    _DEFAULT_CONFIG_FILE = './etc/config.json'    
    
    def __init__(self):
        self._config = None
        self._options = None
        self._logger = None
        
    def setup(self, args=None):
        """
        Sets up the program
        """
        # parse the command line arguments
        parser = argparse.ArgumentParser(description='Download your Google Drive')
        parser.add_argument('command', choices=['download', 'login', 'erase'],
                            nargs='?', default='download',
                            help="Command to execute")
        parser.add_argument('-c', '--config', dest='configuration_file', action='store', 
                            metavar='CONFIG', default=self._DEFAULT_CONFIG_FILE,
                            help='Path to configuration file (CONFIG)')
        parser.add_argument('--debug', dest='debug', 
                            action='store_true', default=False,
                            help='Override logging level to output debug messages')
        parser.add_argument('--remove-creds', dest='remove_credentials', 
                            action='store_true', default=False,
                            help='Remove locally stored credentials (erase command)')
        parser.add_argument('--dry-run', dest='dry_run', action='store_true',
                            help='Simulated output only')
        parser.add_argument('--ignore-modtime', dest='ignore_modtime', 
                            action='store_true', default=False,
                            help="Ignore the modification time and overwrite everything")
        self._options = parser.parse_args(args=args)
        
        # load the configuration
        self._load_configuration( self._options.configuration_file )

        
        # set up logging and credential manager
        # NOTE: this loop is required to ensure credentials for SMTPHandler
        # are always passed in as a tuple and not a list
        for handler in self._config[u'logging'][u'handlers'].itervalues():
            if handler[u'class'] == u'logging.handlers.SMTPHandler':
                handler[u'credentials'] = tuple(handler[u'credentials'])
        dictConfig(self._config[u'logging'])
        self._logger = logging.getLogger('drive_backup')
        if self._options.debug:
            self._logger.setLevel(logging.DEBUG)
        
        self._logger.debug('Loading credential manager')
        self._credential_manager = CredentialManager(self._config[u'credentials'][u'store'][u'path'],
                                                     self._options.dry_run)

    def run(self):
        """
        Runs the selected command
        """
        method_to_call = getattr(self, self._options.command)
        method_to_call()
        
    def report_error(self, error):
        """
        Reports an error to the necessary consumers
        """
        if self._logger:
            self._logger.error(error)
        else:
            print >>sys.stderr, error
        
    def login(self):
        """
        Log in the user to cache the credentials
        """
        self._logger.debug('Running interactive login to cache credentials')
        
        credential_config = self._config[u'credentials']
        self._credential_manager.get_client_credentials_intractive(
            client_id=credential_config[u'account'][u'client_id'], 
            client_secret=credential_config[u'account'][u'client_secret'], 
            persist=True)
        
    def erase(self):
        """
        Erases local data
        """
        self._logger.info('Erasing all local files')
        storage = Storage(self._config, self._options.dry_run)
        storage.erase()
        
        if self._options.remove_credentials:
            self._logger.info('Erasing local credential store')
            self._credential_manager.remove_client_credentials()
            
    def download(self):
        """
        Downloads the files
        """
        
        self._logger.info('Checking Google Drive')
        
        # load the credentials
        credentials = self._credential_manager.load_client_credentials(
            self._config[u'credentials'][u'account'][u'client_id'])
        
        # compile the exclusion list and evaluator
        exclusions = []
        for exclusion_str in self._config[u'backup'][u'exclusions']:
            exclusions.append(re.compile(exclusion_str))
            
        def is_excluded_file(pathname):
            """
            Predicate to determine if a file should be excluded
            """
            for exclusion in exclusions:
                if exclusion.search(pathname):
                    return True
            return False
        
        # create an authorized REST client
        http = httplib2.Http()
        http = credentials.authorize(http)
        drive_service = build('drive', 'v2', http=http)
        
        # prepare the storage hierarchy
        drive_download = GoogleDriveDownload(self._config, 
                                             drive_service, 
                                             self._options.dry_run)
        self._logger.debug('Retrieving folder hierarchy...')
        (all_folders, folder_hierarchy) = drive_download.get_folder_hierarchy()
        storage = Storage(self._config, self._options.dry_run)
        if not self._options.dry_run:
            storage.prepare_storage(all_folders, folder_hierarchy) 
        
        # download all the files
        local_root_folder = storage.get_root_folder()
        for curr_folder_id in all_folders.iterkeys():
            relative_folder_path = drive_download.get_relative_folder_path(curr_folder_id, all_folders)
            for curr_file in drive_download.iterfolder(curr_folder_id):
                
                # determine if the current file should be skipped due to 
                # configured exclusions
                relative_pathname = os.path.sep.join(
                    [ relative_folder_path, 
                     drive_download.get_filename(curr_file)])
                if is_excluded_file(relative_pathname):
                    self._logger.debug('Excluding {0}'.format(relative_pathname))
                    continue
                
                # determine if the file should be skipped due to modification time
                if relative_pathname[0] == '/':
                    relative_pathname = relative_pathname[1:] 
                abs_pathname = os.path.sep.join( [local_root_folder, relative_pathname] )
                if not (self._options.ignore_modtime or 
                        self._drive_file_is_newer(curr_file, abs_pathname)):
                    self._logger.debug('Skipping {0} as there has been no change'.format(relative_pathname))
                    continue
                
                self._logger.info('Downloading {0}'.format(relative_pathname))
                drive_download.download_file(curr_file, abs_pathname)
        

    def _load_configuration(self, config_path ):
        """
        Loads the JSON configuration file
        """
        with open( config_path, 'rt') as fp:
            self._config = json.load(fp)


    def _drive_file_is_newer(self, drive_fileobj, filepath):
        """
        Determine if the drive file is newer than the file in storage
        """
        if not os.path.exists(filepath):
            return True
        
        drive_mtime = time.strptime(drive_fileobj[u'modifiedDate'],"%Y-%m-%dT%H:%M:%S.%fZ")
        finfo = os.stat(filepath)
        return time.mktime(drive_mtime) > finfo.st_mtime
        

def main():
    """
    ... Main Program ...
    """
    main_program = MainProgram()
    try:
        main_program.setup()
        main_program.run()   
        
        
    except Exception as e:
        # handle any exceptions
        main_program.report_error(e)
        sys.exit(1)

if __name__ == '__main__':
    """
    ... Main entry point ...
    """
    main()
