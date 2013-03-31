from smtplib import SMTP, SMTP_SSL
from email.mime.text import MIMEText


class EmailNotifier:
    """
    Email notifier
    """
    def __init__(self, config):
        self._config = config['notifications']['email']
    
    def report_error(self, error_msg):
        """
        Sends an error notifications
        """
        smtp_client = None
        try:
            msg = MIMEText(error_msg)
            msg['From'] = self._config['from']
            msg['Subject'] = self._config['subject']
            msg['To'] = ', '.join(self._config['recipients'])
            
            # use system SMTP configuration if one does not exist
            smtp_config = self._config['smtp']
            if not smtp_config:
                smtp_client = SMTP('localhost')
            # otherwise, use the explicitly specified SMTP configuration
            else:
                smtp_client = SMTP(host=smtp_config['host'],
                                port=smtp_config['port'])
                if smtp_config['type'] == 'ssl':
                    smtp_client.ehlo()
                    smtp_client.starttls()
                    smtp_client.ehlo()                    

                smtp_login = smtp_config['login']
                if smtp_login:
                    smtp_client.login(smtp_login['username'], smtp_login['password'])
                    
            # send the email
            smtp_client.sendmail(self._config['from'], 
                          self._config['recipients'], 
                          msg.as_string())
            
        finally:
            if smtp_client:
                smtp_client.quit()
