import os
import shelve
from oauth2client.client import OAuth2WebServerFlow

class CredentialError(Exception):
    """
    Exception class for all credential operations
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
    
class CredentialManager:
    """
    Manages all credentials
    """
    def __init__(self, storage_pathname, dry_run):
        self._store_pathname = storage_pathname
        if type(self._store_pathname) == unicode:
            self._store_pathname = self._store_pathname.encode('ascii')
        self._dry_run = dry_run
    
    def load_client_credentials(self, client_id):
        """
        Loads a user's credential from the local store
        """
        if type(client_id) == unicode:
            client_id = client_id.encode('ascii')
        store = self._load_credential_store()
        if client_id not in store:
            raise CredentialError('Credential not found')
        
        credentials = store[client_id]
        store.close()
        return credentials
            
    
    def store_client_credentials(self, client_id, credentials):
        """
        Stores the user's credential locally
        """
        if self._dry_run:
            return
        if type(client_id) == unicode:
            client_id = client_id.encode('ascii')
        store = self._load_credential_store()
        store[client_id] = credentials
        store.close()
    
    def get_client_credentials_intractive(self, client_id, client_secret, persist=False):
        """
        Interactively retrieves the crendential for a user_id
        
        client_id -- user identifier
        client_secret -- user's secret key
        persist -- True to immediately store the credential, False otherwise  (default)
        """
        if type(client_id) == unicode:
            client_id = client_id.encode('ascii')
        if type(client_secret) == unicode:
            client_secret = client_secret.encode('ascii')
        
        flow = OAuth2WebServerFlow(client_id, client_secret, self._OAUTH_SCOPE, 
                                   redirect_uri=self._REDIRECT_URI)
        authorize_url = flow.step1_get_authorize_url()
        print 'Go to the following link in your browser: ' + authorize_url
        code = raw_input('Enter verification code: ').strip()
        credentials = flow.step2_exchange(code)
        
        if persist:
            self.store_client_credentials(client_id, credentials)
            
        return credentials
    
    def remove_client_credentials(self):
        """
        Remove the locally stored credentials
        """
        if self._dry_run:
            return
        os.unlink(self._store_pathname)

    def _load_credential_store(self):
        """
        Returns the credential store if the file exists
        """    
        try:
            return shelve.open(self._store_pathname)

        except Exception:
            raise CredentialError('Unable to open credential store: ' + self._store_pathname) 
    
    def _save_credential_store(self, store):
        """
        Flushes and closes the credential store
        """
        store.close()
        
    _OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'
    _REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
