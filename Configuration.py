__author__ = 'doms'

import sys
import os
import ConfigParser
import logging

class Configuration(object):
    def __init__(self):
        self.FOLDER_SYSTEM = "%Y/%m/%d/"  # %H/%M/"
        self.DATABASE_FILE_PATH = None
        self.BACKUP_FOLDER_PATH = None
        self.MAIL_SERVER = None
        self.MAIL_USER = None
        self.MAIL_PASSWORD = None
        self.MAIL_PORT = None
        self.SAVE_EML = True
        self.ONLY_LAST_X_DAYS = None

        # Load Configuration from ini
        CONFIG = ConfigParser.RawConfigParser()
        try:
            if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
                CONFIG.read(sys.argv[1])
                print "Loaded configuration: %s" % sys.argv[1]
            else:
                CONFIG.read("./config.ini")
                print "Loaded default configuartion from ./config.ini"
        except Exception as e:
            print "Could not load Configuration: %s" % e
            exit(1)

        #Logging
        try:
            logging_level = CONFIG.get('logging', 'level')
            if logging_level == 'DEBUG':
                logging_level = logging.DEBUG
            elif logging_level == 'INFO':
                logging_level = logging.INFO
            elif logging_level == 'WARNING':
                logging_level = logging.WARNING
            elif logging_level == 'ERROR':
                logging_level = logging.ERROR
            else:
                logging_level = logging.INFO
        except Exception as e:
            logging_level = logging.INFO

        try:
            logging_file = CONFIG.get('logging', 'logfile')
            try:
                logging_clear = CONFIG.get('logging', 'remove_old')
                if logging_clear == 'True':
                    os.remove(logging_file)
            except:
                pass

            logging.basicConfig(format='%(levelname)s:%(message)s', filename=logging_file, level=logging_level)

        except:
            logging.basicConfig(format='%(levelname)s:%(message)s', level=logging_level)


        #most important parameters
        try:
            self.MAIL_SERVER = CONFIG.get('mail', 'imap_server')
            self.MAIL_USER = CONFIG.get('mail', 'imap_user')
            self.MAIL_PASSWORD = CONFIG.get('mail', 'imap_password')
            self.DATABASE_FILE_PATH = CONFIG.get('backup', 'database_file')
            self.BACKUP_FOLDER_PATH = CONFIG.get('backup', 'backup_folder')
        except Exception as e:
            logging.critical("Could not load parameters because of %s", e)
            print "You need to define a config.ini which could look as follows:"
            print "[mail]"
            print "imap_server = imap.mail.com"
            print "imap_user = name@mail.com"
            print "imap_password = password123"
            print ""
            print "[backup]"
            print "database_file = ./database.db"
            print "backup_folder = ./backup-mail/"
            print "also_save_as_eml = True"
            print ""
            print "You can also pass the ini by parameter and give it another name as config.ini"
            print "You can also define imap_port to get another port"
            exit(1)

        try:
            self.MAIL_PORT = CONFIG.get('mail', 'imap_port')
            logging.info("Using port: %s", self.MAIL_PORT)
        except:
            self.MAIL_PORT = None  # Default

        try:
            self.ONLY_LAST_X_DAYS = int(CONFIG.get('backup', 'only_last_x_days'))
            print "Only checking Mails of the last ", self.ONLY_LAST_X_DAYS, " days"
        except:
            self.ONLY_LAST_X_DAYS = None

        #EML-Parameter
        try:
            self.SAVE_EML = False
            if CONFIG.get('backup', 'also_save_as_eml') == 'True':
                self.SAVE_EML = True
        except:
            pass