#!/usr/bin/env python

# Downloads a file list

import argparse
import httplib2
import pprint
import json
import logging
import sys

from apiclient.discovery import build

from auth.credential import CredentialManager

DEFAULT_CONFIG_FILE = './etc/config.json'
OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'


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
    try:
        
        # parse the command line arguments
        parser = argparse.ArgumentParser(description='Download all Google docs')
        parser.add_argument('-c', '--config', dest='configuration_file', action='store', 
                            metavar='CFG_FILE', default=DEFAULT_CONFIG_FILE,
                            help='Path to configuration file')
        parser.add_argument('--log', dest='logging_level', action='store',
                            metavar='LOGLEVEL', default='WARN',
                            help='Set the logging level')
        parser.add_argument('-u', '--user-credentials', dest='cache_credentials', action='store_true',
                            help="Cache the user's credentials")
        options = parser.parse_args()

        # set up logging
        logging.basicConfig(level=getattr(logging, options.logging_level))
        logging.getLogger('oauth2client.util').addHandler(logging.StreamHandler())

        # load the configuration and credential manager
        config = load_configuration( options.configuration_file )
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
        
        # create an authorized REST client
        http = httplib2.Http()
        http = credentials.authorize(http)
        drive_service = build('drive', 'v2', http=http)
        
        # list all files
        list_results = drive_service.files().list().execute()
        pprint.pprint(list_results)
        
    except Exception as e:
        print >>sys.stderr, e
        sys.exit(1)

if __name__ == '__main__':
    """
    ... Main entry point ...
    """
    main()
