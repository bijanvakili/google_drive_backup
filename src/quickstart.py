#!/usr/bin/env python

# Downloads a file list

import argparse
import httplib2
import pprint
import json
import logging

from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials

DEFAULT_CONFIG_FILE = './etc/config.json'
OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'


# loads the JSON configuration file
def load_configuration( config_path ):
    with open( config_path, 'rt') as fp:
        return json.load(fp)

# loads the API client credentials
def load_credentials( config ):
    with open( config['credentials']['account']['private_key']['path'], 'rb' ) as fp:
        private_key = fp.read()
    
    return SignedJwtAssertionCredentials(service_account_name=config['credentials']['account']['email'],
                                          private_key=private_key,
                                          scope=OAUTH_SCOPE,
                                          private_key_password=config['credentials']['account']['private_key']['password'])


# ... Main program ...
if __name__ == '__main__':

    # load the configuration
    parser = argparse.ArgumentParser(description='Download all Google docs')
    parser.add_argument('-c', '--config', dest='configuration_file', action='store', 
                        metavar='CFG_FILE', default=DEFAULT_CONFIG_FILE,
                        help='Path to configuration file')
    parser.add_argument('--log', dest='logging_level', action='store',
                        metavar='LOGLEVEL', default='WARN',
                        help='Set the logging level')
    options = parser.parse_args()
    config = load_configuration( options.configuration_file )
    
    # set up logging
    logging.basicConfig(level=getattr(logging, options.logging_level))
    logging.getLogger('oauth2client.util').addHandler(logging.StreamHandler())
    
    # load the credentials
    credentials = load_credentials(config)
    
    # create an authorized REST client
    http = httplib2.Http()
    http = credentials.authorize(http)
    drive_service = build('drive', 'v2', http=http)
    
    # list all files
    list_results = drive_service.files().list().execute()
    pprint.pprint(list_results)
