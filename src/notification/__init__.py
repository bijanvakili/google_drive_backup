from smtplib import SMTP, SMTP_SSL
from email.mime.text import MIMEText


class EmailNotifier:
    """
    Email notifier
    """
    def __init__(self, config):
        self._config = config[u'notifications'][u'email']
        self._config.__dict__.update()
    
    def report_error(self, error_msg):
        """
        Sends an error notifications
        """
        smtp_client = None
        try:
            msg = MIMEText(error_msg)
            msg['From'] = self._config[u'from']
            msg['Subject'] = self._config.subject
            msg['To'] = ', '.join(self._config.recipients)
            
            # use system SMTP configuration if one does not exist
            smtp_config = self._config.get(u'smtp')
            if not smtp_config:
                smtp_client = SMTP('localhost')
            # otherwise, use the explicitly specified SMTP configuration
            else:
                smtp_config.__dict__.update()
                smtp_client = SMTP(host=smtp_config.host,
                                port=smtp_config.port)
                if smtp_config.type == u'ssl':
                    smtp_client.ehlo()
                    smtp_client.starttls()
                    smtp_client.ehlo()                    

                smtp_login = smtp_config.get('login')
                if smtp_login:
                    smtp_client.login(smtp_login[u'username'], smtp_login[u'password'])
                    
            # send the email
            smtp_client.sendmail(self._config.get(u'from'), 
                          self._config.recipients, 
                          msg.as_string())
            
        finally:
            if smtp_client:
                smtp_client.quit()
