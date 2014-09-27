__author__ = 'doms'


class Statistics(object):
    def __init__(self, initial_amount_of_emails_in_db):
        # Stats
        self.emails_in_database = initial_amount_of_emails_in_db
        self.emails_added = 0
        self.attachments_added = 0
        self.failed_folders = 0
        self.failed_mails = 0
        self.failed_attachments = 0

    def email_successful_added(self):
        self.emails_added+=1

    def email_failed_to_add(self):
        self.failed_mails+=1

    def folder_failed_to_backup(self):
        self.failed_folders+=1

    def failed_to_safe_attachment(self):
        self.failed_attachments+=1

    def succesfully_safed_attachment(self):
        self.attachments_added +=1

    def toString(self):
        return "==STATS==========================================\n" + str(
            self.emails_in_database+self.emails_added) + " emails in database\n" + str(
            self.emails_added) + " new emails downloaded\n" + str(
            self.attachments_added) + " new attachments downloaded\n" + str(
            self.failed_folders) + " folders failed to download" + str(
            self.failed_mails) + " mails failed to download\n" + str(
            self.failed_attachments) + " attachments failed to download\n"
