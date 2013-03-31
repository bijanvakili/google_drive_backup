#!/usr/bin/env python

"""
Downloads your Google drive for backup
"""
# TODO handle modification time (or override to download all)
# TODO logging configuration
# TODO cron job
# TODO makefile and packaging

import argparse
import httplib2
import json
import logging
import os
import re
import sys

from apiclient.discovery import build

from auth.credential import CredentialManager
from backup.google_drive import GoogleDriveDownload 
from backup.storage import Storage
from notification import EmailNotifier

DEFAULT_CONFIG_FILE = './etc/config.json'


def convert_tree_unicode_to_str(tree):
    """
    Recursive function to convert all unicode strings in a tree to regular strings
    """
    if isinstance(tree, dict):
        return {convert_tree_unicode_to_str(key): convert_tree_unicode_to_str(value) for key, value in tree.iteritems()}
    elif isinstance(tree, list):
        return [convert_tree_unicode_to_str(element) for element in tree]
    elif isinstance(tree, unicode):
        return tree.encode('utf-8')
    else:
        return tree

def load_configuration( config_path ):
    """
    Loads the JSON configuration file
    """
    with open( config_path, 'rt') as fp:
        return convert_tree_unicode_to_str(json.load(fp))


def main():
    """
    ... Main Program ...
    """
    config = None
    try:
        # parse the command line arguments
        parser = argparse.ArgumentParser(description='Download all Google docs')
        parser.add_argument('-c', '--config', dest='configuration_file', action='store', 
                            metavar='CFG_FILE', default=DEFAULT_CONFIG_FILE,
                            help='Path to configuration file')
        parser.add_argument('--log', dest='logging_level', action='store',
                            metavar='LOGLEVEL', default='WARN',
                            help='Set the logging level')
        parser.add_argument('-u', '--user-credentials', dest='cache_credentials', 
                            action='store_true', default=False,
                            help="Cache the user's credentials")
        parser.add_argument('--dry-run', dest='dry_run', action='store_true',
                            help='Simulated Output only')
        options = parser.parse_args()
            
        # set up logging
        logging.basicConfig(level=getattr(logging, options.logging_level))
        logging.getLogger('oauth2client.util').addHandler(logging.StreamHandler())
        logger = logging.getLogger('drive_backup')
        logger.addHandler(logging.StreamHandler())

        # load the configuration and credential manager
        config = load_configuration( options.configuration_file )
        config['dry_run'] = options.dry_run
        credential_manager = CredentialManager(config['credentials']['store']['path'])
        
        # interactively cache the user's credentials if necessary
        if options.cache_credentials:
            credential_manager.get_client_credentials_intractive(
                client_id=config['credentials']['account']['client_id'], 
                client_secret=config['credentials']['account']['client_secret'], 
                persist=True)
            sys.exit(0)
        
        
        # load the credentials
        credentials = credential_manager.load_client_credentials(config['credentials']['account']['client_id'])
        
        # compile the exclusion list and evaluator
        exclusions = []
        for exclusion_str in config['backup']['exclusions']:
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
        drive_download = GoogleDriveDownload(config, drive_service)
        (all_folders, folder_hierarchy) = drive_download.get_folder_hierarchy()
        storage = Storage(config, all_folders, folder_hierarchy)
        storage.prepare_storage() 
        
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
                    logger.info('Excluding {0}'.format(relative_pathname))
                    continue
                
                abs_pathname = os.path.sep.join( [local_root_folder, relative_pathname] )
                drive_download.download_file(curr_file, abs_pathname)
        
    except Exception as e:
        if logger:
            logger.error(e)
        else:
            print >>sys.stderr, e
            
        if config and 'email' in config['notifications']:
            notifier = EmailNotifier(config)
            notifier.report_error(str(e))
            
        sys.exit(1)

if __name__ == '__main__':
    """
    ... Main entry point ...
    """
    main()
