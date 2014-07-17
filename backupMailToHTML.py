#!/usr/bin/env python

import sys
import imaplib
import email
import datetime
import hashlib
import os
import cgi
import re
import ConfigParser
import logging
from email.header import decode_header


#Configuration
FOLDER_SYSTEM = "%Y/%m/%d/" #%H/%M/"
DATABASE_FILE_PATH =None
BACKUP_FOLDER_PATH =None
MAIL_SERVER=None
MAIL_USER=None 
MAIL_PASSWORD=None 
MAIL_PORT=None
SAVE_EML = True


#Load Configuration from ini
CONFIG = ConfigParser.RawConfigParser()
try:
    if len(sys.argv)>1 and os.path.isfile(sys.argv[1]):
        CONFIG.read(sys.argv[1])
        print "Loaded configuration: %s"%sys.argv[1]
    else:
        CONFIG.read("./config.ini")
        print "Loaded default configuartion from ./config.ini"
except Exception as e:
    print "Could not load Configuration: %s"%e
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
            
    logging.basicConfig(format='%(levelname)s:%(message)s',filename=logging_file, level=logging_level)
    
except:    
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging_level)


#most important parameters
try:
    MAIL_SERVER = CONFIG.get('mail', 'imap_server')
    MAIL_USER = CONFIG.get('mail', 'imap_user')
    MAIL_PASSWORD= CONFIG.get('mail', 'imap_password')
    DATABASE_FILE_PATH = CONFIG.get('backup','database_file')
    BACKUP_FOLDER_PATH = CONFIG.get('backup','backup_folder')
except Exception as e:
    logging.critical("Could not load parameters because of %s",e)
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
    MAIL_PORT = CONFIG.get('mail', 'imap_port')
    logging.info("Using port: %s", MAIL_PORT)
except:
    MAIL_PORT = None #Default

#EML-Parameter
try:
    SAVE_EML= False
    if CONFIG.get('backup','also_save_as_eml')=='True':
        SAVE_EML = True
except:
    pass

#Stats
STATS_EMAIL_IN_DATABASE = 0
STATS_ADDED_EMAILS = 0
STATS_ADDED_ATTACHMENTS = 0
STATS_FAILED_FOLDERS = 0
STATS_FAILED_EMAILS = 0
STATS_FAILED_ATTACHMENTS = 0

#Load Hashcodes from File
DATABASE = set()
try:
    DATABASE_FILE = open(DATABASE_FILE_PATH, 'r')
except:
    DATABASE_FILE = open(DATABASE_FILE_PATH, 'w+')
    logging.info("Created New Database %s",DATABASE_FILE_PATH)

print "Loading Database...."
for line in DATABASE_FILE:
    DATABASE.add(line.replace('\n',''))
logging.info("Loaded %i mail hash values from database", len(DATABASE))
STATS_EMAIL_IN_DATABASE = len(DATABASE)
DATABASE_FILE.close()
#Open Database-File for appending new HashCodes
DATABASE_FILE = open(DATABASE_FILE_PATH, 'a') 

print "Connecting to Server..."
#Init Mail Connection
MAIL_CONNECTION = imaplib.IMAP4_SSL(MAIL_SERVER, MAIL_PORT) if MAIL_PORT else imaplib.IMAP4_SSL(MAIL_SERVER) 
try:
    MAIL_CONNECTION.login(MAIL_USER,MAIL_PASSWORD)
    logging.info("Successfully connected to %s@%s", MAIL_USER,MAIL_SERVER)
except imaplib.IMAP4.error as e:
    logging.error("Could not connect to %s@%s", MAIL_USER,MAIL_SERVER)
    logging.error("Reason: %s", e)
    exit(1)

print "Running Backup...."

#fetches the mailboxes/mailfolders lik "INBOX", "INBOX.Archives.2011" ('.' is separator)
# and gives it back as List
def fetchMailFolders():
    check, mailfolders_raw = MAIL_CONNECTION.list()
    mailfolders_parsed = []
    if check == 'OK':
        for folder_information in mailfolders_raw:
            #folder_information looks for example like:
            # (\HasNoChildren \UnMarked) "." "INBOX.Archives.2011"
            folder_information = folder_information.split('\"')
            #Some folders are only for navigation. They have the parameter (\Noselect)
            if "Noselect" not in folder_information[0]:
                for folder_name in folder_information[-1:0:-1]:
                    if folder_name:
                        while folder_name[0]==' ':
                            folder_name = folder_name[1:]
                        mailfolders_parsed.append(folder_name)
                        break;
    else:
        logging.critical("Could not load mailboxes: %s",check)
        exit(1)
        
    logging.debug("Mail Folders: %s", str(mailfolders_raw))
    return mailfolders_parsed

class DecodeError(Exception):
    pass

def decode_string(string, encoding):
    try:
        if encoding:
            return cgi.escape(unicode(string, encoding)).encode('ascii', 'xmlcharrefreplace')
        else:
            return cgi.escape(string).encode('ascii', 'xmlcharrefreplace')
    except Exception as e:
        logging.warning("Encoding failed: Trying brute force encoding (should work) - %s",str(e))
        for charset in ("utf-8", 'latin-1', 'iso-8859-1', 'us-ascii', 'windows-1252','us-ascii'):
            try:
                ret = cgi.escape(unicode(string, charset)).encode('ascii', 'xmlcharrefreplace')
                logging.info("Brute force encoding successfull: %s", charset)
                return ret
            except Exception:
                continue
        raise DecodeError("Could not decode string")
        
def encode_unicode(string, encoding):
    try:
        if encoding:
            return unicode(string, encoding).encode('ascii', 'xmlcharrefreplace')
        else:
            return string.encode('ascii', 'xmlcharrefreplace')
    except Exception as e:
        logging.warning("Encoding failed: Trying brute force encoding (should work) - %s",str(e))
        for charset in ("utf-8", 'latin-1', 'iso-8859-1', 'us-ascii', 'windows-1252','us-ascii'):
            try:
                ret = unicode(string, charset).encode('ascii', 'xmlcharrefreplace')
                logging.info("Brute force encoding successfull: %s", charset)
                return ret
            except Exception:
                continue
        raise e
# This object wraps the imaplib and email for a lazy access of the important elements of an email
# Getting the Header and the Hashcode will only need a few KB independent of the mail-size
# If you want to have the content, the whole mail with attachments will be fetched
class LazyMail(object):
    def __init__(self, uid):
        self.__uid = uid
        self.__fetchedHeader = None
        self.__headerhash = None
        self.__parsedMail = None
        self.__subject = None
        self.__from = None
        self.__to = None
        self.__date = None
        self.__maildataRaw = None

    #Returns a non formated or parsed header
    def getHeader(self):
        if self.__fetchedHeader:
            return self.__fetchedHeader
        #print "Fetch Header..."
        check, maildata_raw = MAIL_CONNECTION.uid("FETCH", self.__uid, '(RFC822.HEADER)')
        if check == 'OK':
            self.__fetchedHeader = str(maildata_raw)
            return self.__fetchedHeader
        else:
            logging.warning("Could not fetch mail header for ", self.__uid)

    # Lazy fetches the Header (1000 characters~4k per uid) and calculates a hash of it for avoid multiple backups
    # (Important for mails with attachments)
    # You can check 10.000 mails for backup with only 40MB of traffic.
    # Nearly all mail provider should attach a real UID to the header, meaning
    # equal headers should not exist.
    # uid(string): the (folder local) uid number as string
    def getHashcode(self):
        if not self.__headerhash:
            self.__headerhash = hashlib.md5(self.getHeader()).hexdigest()
        return self.__headerhash

    #Return the email class of the lib email
    def getParsedMail(self):
        if not self.__parsedMail:
            self.__parsedMail = email.message_from_string(self.getRawMaildata()[0][1])
        return self.__parsedMail
    
    #Lazy fetches the maildata    
    def getRawMaildata(self):
        if not self.__maildataRaw:
            check, self.__maildataRaw = MAIL_CONNECTION.uid("FETCH", self.__uid, '(RFC822)')
            if check == 'OK':
                logging.debug("Successfully downloaded mail: %s", self.getHashcode())
            else:
                logging.warning("Could not download mail: %s", self.getHashcode())
        return self.__maildataRaw       

    #Returns the well formated 'from'
    def getFrom(self):
        if not self.__from:
            mail_from = email.utils.parseaddr(self.getParsedMail().get('From'))[1]
            mail_from_encoding = decode_header(self.getParsedMail().get('From'))[0][1]
            if not mail_from_encoding:
                mail_from_encoding = "utf-8"
            try:
                self.__from = decode_string(mail_from, mail_from_encoding) #cgi.escape(unicode(mail_from, mail_from_encoding)).encode('ascii', 'xmlcharrefreplace')
            except Exception as e:
                logging.warning("Could not decode 'from' because of %s",e) 
                self.__from="(Could not decode)"
        return self.__from

    #return the well formated 'subject'
    def getSubject(self):
        if not self.__subject:
            
            mail_subject = decode_header(self.getParsedMail().get('Subject'))[0][0]
            mail_subject_encoding = decode_header(self.getParsedMail().get('Subject'))[0][1]
            if not mail_subject_encoding:
                mail_subject_encoding = "utf-8"

            if not mail_subject:
                mail_subject = "(No Subject)"
            
            try:
                self.__subject = decode_string(mail_subject,mail_subject_encoding) #cgi.escape(unicode(mail_subject, mail_subject_encoding)).encode('ascii', 'xmlcharrefreplace')
            except Exception as e:
                logging.warning("Could not decode subject because of %s",e) 
                self.__subject = "(Could not decode)"

        return self.__subject

    #returns the well formated 'to'
    def getTo(self):
        if not self.__to:
            mail_to = email.utils.parseaddr(self.getParsedMail().get('To'))[1]
            mail_to_encoding = decode_header(self.getParsedMail().get('To'))[0][1]
            if not mail_to_encoding:
                mail_to_encoding = "utf-8"
            try:
                self.__to = decode_string(mail_to, mail_to_encoding) #cgi.escape(unicode(mail_to, mail_to_encoding)).encode('ascii', 'xmlcharrefreplace')
            except Exception as e:
                logging.warning("Could not decode 'to' because of %s",e) 
                self.__to = "(Could not decode)"
        return self.__to

    #returns the date as string, like "Wed, 18 Apr 2014 10:14:48 +0200"
    def getDate(self):
        if not self.__date:
            mail_date = decode_header(self.getParsedMail().get('Date'))[0][0]
            self.__date = mail_date
        return self.__date

    #Returns the HTML and Text Content of the mail (no attachments or else, just human-written-text).
    #The Return-Value is a Dictionary with the entries 'text'->String and 'html'->String
    #A mail can have a text-part and a html-part. Often it contains the same, since html looks nicer but not all clients have html (cell phones,...)
    # This function is taken from https://github.com/RaymiiOrg/NoPriv
    def getContent(self):
        content_of_mail = {}
        content_of_mail['text'] = ""
        content_of_mail['html'] = ""
        
        check = True

        for part in self.getParsedMail().walk():
            part_content_type = part.get_content_type()
            part_charset = part.get_charsets()
            if part_content_type == 'text/plain':
                part_decoded_contents = part.get_payload(decode=True)
                try:
                    content_of_mail['text'] += decode_string(str(part_decoded_contents), part_charset[0])# cgi.escape(unicode(str(part_decoded_contents), part_charset[0])).encode('ascii', 'xmlcharrefreplace')
                except Exception as e:
                    content_of_mail['text'] += "Error decoding mail contents."
                    logging.error("Could not decode text content of mail (%s,%s) because of %s",self.getDate(), self.getSubject(), e)
                    check = False
            
                continue
            elif part_content_type == 'text/html':
                part_decoded_contents = part.get_payload(decode=True)
                try:
                    content_of_mail['html'] += encode_unicode(str(part_decoded_contents), part_charset[0])
                except Exception as e:
                    content_of_mail['html'] += "Error decoding mail contents."
                    logging.error("Could not decode html content of mail (%s,%s) because of %s",self.getDate(), self.getSubject(), e)
                    check = False

                continue
        return check, content_of_mail
        
    def getBaseFilename(self):
        return self.getHashcode()
        
    def saveEMLtoFile(self, folder_path):
       full_path = os.path.join(folder_path,self.getBaseFilename()+".eml")
       emlfile = open(full_path, 'w')
       emlfile.write(self.getRawMaildata()[0][1])
       emlfile.close()
       logging.debug("Saved EML %s",full_path)
           


#Get Mail UIDs of mail_folder (in mailfolders_parsed)
#They are only unique in mail_folder and session!
def getUIDs(mail_folder):
    check, uids_raw = MAIL_CONNECTION.uid('SEARCH', None, "ALL")
    if check == 'OK':
        MAIL_UIDs = uids_raw[0].split()
        return MAIL_UIDs
    else:
        logging.warning("Could not fetch UIDs for mailbox %s", mail_folder)
        return []


#adds a hashcode of a mail to the database such that it won't be fetched
# another time with all its attachments and co
# the hashcode is generated by getHashcode(uid)
def addHashCodeToDatabase(hashcode):
    DATABASE_FILE.write(hashcode+"\n") #The \n has to be removed by reading
    DATABASE.add(hashcode)
    logging.debug("Added hashcode %s to database", hashcode)
    global STATS_EMAIL_IN_DATABASE
    STATS_EMAIL_IN_DATABASE +=1



#Gets a LazyMail and saves it to disk
#It will use the Hashcode as Filename and the date as path
#The Date-Path can be configured
#Returns true if successful. If it returns false there was at least a little failure. No rollback is made
def saveMailToHardDisk(lazy_mail):
    #Getting path from date
    parsed_mail = lazy_mail.getParsedMail()
    date_raw = email.utils.parsedate_tz(parsed_mail['Date'])
    if date_raw:
        local_date_raw = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_raw))
        path = local_date_raw.strftime(FOLDER_SYSTEM)
    else:
        path = "NoDate/"

    #Save to file
    try:
        #Create Path if not exist
        mail_folder_path = os.path.join(BACKUP_FOLDER_PATH,path)
        if not os.path.exists(mail_folder_path):
            os.makedirs(mail_folder_path)
        
        #save eml file which can be opened with thunderbird (is more or less what the server has returned)
        if SAVE_EML:
            eml_path = os.path.join(mail_folder_path, "eml",)
            if not os.path.exists(eml_path):
                os.makedirs(eml_path)
            lazy_mail.saveEMLtoFile(eml_path)
        
        #Save attachments: If there are no, False will be returned
        check_attachments, attachments = saveAttachmentsToHardDisk(lazy_mail, mail_folder_path)

        #Create HTML-File
        full_path =os.path.join(mail_folder_path,lazy_mail.getHashcode())+".html" 
        file_message_without_attachment = open(full_path, 'w')
        check_html = writeToHTML(lazy_mail, attachments, file_message_without_attachment)
        file_message_without_attachment.close()

    except Exception as e:
        #If anything has failed
        logging.error("Failed to save mail (%s,%s) because of %s",lazy_mail.getDate(), lazy_mail.getSubject(), e)
        return False
    
    if check_attachments and check_html: 
        logging.info("Saved mail (From: %s, Subject: %s) to %s", lazy_mail.getFrom(), lazy_mail.getSubject(), full_path)
        return True
    elif check_attachments or check_html: 
        logging.info("Partly saved mail (From: %s, Subject: %s) to %s", lazy_mail.getFrom(), lazy_mail.getSubject(), full_path)
        return False
    else:
        logging.info("Could not save mail (From: %s, Subject: %s)", lazy_mail.getFrom(), lazy_mail.getSubject())
        return False


#Writes a lazy_mail to a given HTML-File
def writeToHTML(lazy_mail, attachments, html_file):
    check = True
    try:
        #HTML-Header
        html_file.write("<!DOCTYPE html> <html lang=\"en\"> <head> <title>")
        html_file.write(lazy_mail.getSubject())
        html_file.write("</title> <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"> </head> <body> <div class=\"row\"> <div class=\"col-md-12\">")
    
        #HTML-Table with To,From,Subject
        html_file.write("<table boarder=\"1\">\n")
        html_file.write("\t<tr>\n")
        html_file.write("\t\t<td>From: </td>\n")
        html_file.write("\t\t<td>" + lazy_mail.getFrom() + "</td>\n")
        html_file.write("\t<tr>\n")
    
        html_file.write("\t<tr>\n")
        html_file.write("\t\t<td>To: </td>\n")
        html_file.write("\t\t<td>" + lazy_mail.getTo() + "</td>\n")
        html_file.write("\t<tr>\n")
    
        html_file.write("\t<tr>\n")
        html_file.write("\t\t<td>Subject: </td>\n")
        html_file.write("\t\t<td>" + lazy_mail.getSubject() + "</td>\n")
        html_file.write("\t<tr>\n")
    
        html_file.write("\t<tr>\n")
        html_file.write("\t\t<td>Date: </td>\n")
        html_file.write("\t\t<td>" + lazy_mail.getDate() + "</td>\n")
        html_file.write("\t<tr>\n")
    
        #Information in Table if Attachments
        if len(attachments)>0:
            html_file.write("\t<tr>\n")
            html_file.write("\t\t<td>Attachments: </td><td>")
            for attachment in attachments:
                html_file.write("<a href=\""+attachment[0]+"\">"+decode_string(str(attachment[1]), None)+"</a>")
                if attachment is not attachments[-1]:
                    html_file.write(", ")
            html_file.write("</td>\n")
            html_file.write("\t<tr>\n")
    
        html_file.write("</table>\n")
        html_file.write("<div class=\"col-md-8 col-md-offset-1 footer\"> <hr /><div style=\"white-space: pre-wrap;\">")
        #Write content to File
        check, content_of_mail = lazy_mail.getContent()
        if content_of_mail['text']:
            html_file.write("<pre>")
            strip_header = re.sub(r"(?i)<html>.*?<head>.*?</head>.*?<body>", "", content_of_mail['text'], flags=re.DOTALL)
            strip_header = re.sub(r"(?i)</body>.*?</html>", "", strip_header, flags=re.DOTALL)
            strip_header = re.sub(r"(?i)<!DOCTYPE.*?>", "", strip_header, flags=re.DOTALL)
            strip_header = re.sub(r"(?i)POSITION: absolute;", "", strip_header, flags=re.DOTALL)
            strip_header = re.sub(r"(?i)TOP: .*?;", "", strip_header, flags=re.DOTALL)
            html_file.write(strip_header)
            html_file.write("</pre>\n")


        if content_of_mail['html']:
            strip_header = re.sub(r"(?i)<html>.*?<head>.*?</head>.*?<body>", "", content_of_mail['html'], flags=re.DOTALL)
            strip_header = re.sub(r"(?i)</body>.*?</html>", "", strip_header, flags=re.DOTALL)
            strip_header = re.sub(r"(?i)<!DOCTYPE.*?>", "", strip_header, flags=re.DOTALL)
            strip_header = re.sub(r"(?i)POSITION: absolute;", "", strip_header, flags=re.DOTALL)
            strip_header = re.sub(r"(?i)TOP: .*?;", "", strip_header, flags=re.DOTALL)
            html_file.write(strip_header)

        #HTML-Footer
        #html_file.write("</div> <div class=\"col-md-8 col-md-offset-1 footer\"> <hr /><div style=\"white-space: pre-wrap;\">")
        #html_file.write(lazy_mail.getHeader())
        html_file.write("</div></div></body></html>")

    except Exception as e:
        logging.error("Could not write HTML because of %s",e)
        raise e
    
    return check

#Saves the attachments of a LazyMail to disk. Uses the Path 'folder_prefix-filename'
#E.g for folder_prefix="2014/05/03/4a9fd924" and filename="photo.jpg" it will be "2014/05/03/4a9fd924-photo.jpg"
def saveAttachmentsToHardDisk(lazy_mail, folder):
    attachments_tuple_for_html = []
    filename_count = dict() #to handle attachments with same name
    successfull = True
    for part in lazy_mail.getParsedMail().walk():
        try:
            content_maintype = part.get_content_maintype()
            if content_maintype == 'multipart' or content_maintype == 'text' or content_maintype == 'html':
                continue
    
            if part.get('Content-Disposition') == None:
                continue

            try:
                attachment_filename = decode_header(part.get_filename())[0][0]
                attachment_filename_encoding = decode_header(part.get_filename())[0][1]
            except Exception as e:
                logging.error("Could not encode filename")
                attachment_filename = "(could not encode filename)"
                attachment_filename_encoding = None
                successfull = False
            
            if not attachment_filename:
                logging.warning("Empty part in mail. Don't know what to do with it!")
                logging.debug(str(part))
                continue
           
            #put a (x) behind filename if same filename already exists
            if attachment_filename in filename_count:
                logging.debug("Same Filename %s",attachment_filename)
                root, ext = os.path.splitext(attachment_filename)
                attachment_filename = root+"("+str(filename_count[attachment_filename])+")"+ext
                filename_count[attachment_filename] = filename_count[attachment_filename]+1
            else:
                filename_count[attachment_filename] = 1            
           
            attachment_folder_name = os.path.join("attachments",lazy_mail.getHashcode(),"")
            attachment_folder_path = os.path.join(folder, attachment_folder_name) 
            attachments_tuple_for_html += [(attachment_folder_name+attachment_filename,decode_string(attachment_filename, attachment_filename_encoding))]     #TODO   
            
            if not os.path.exists(attachment_folder_path):
                os.makedirs(attachment_folder_path)        
            
            attachment_path = attachment_folder_path+attachment_filename
       
        
            attachment_file_disk = open(attachment_path, "wb")
            attachment_file_disk.write(part.get_payload(decode=True))
            logging.info("Saved attachment %s to %s",attachment_filename, attachment_path)
            global STATS_ADDED_ATTACHMENTS
            STATS_ADDED_ATTACHMENTS += 1
        except Exception as e:
            successfull = False;
            global STATS_FAILED_ATTACHMENTS
            STATS_FAILED_ATTACHMENTS+=1
            logging.error("Failed to save attachment %s: %s", attachment_filename, e)

    return successfull, attachments_tuple_for_html


#goes through all folders and checks the emails
for mailfolder in fetchMailFolders():
    try:
        #SPAM
        if mailfolder[-4:-1].lower() == 'spam':
            logging.info("Skip folder %s",mailfolder)
            continue
        
        folder_state = MAIL_CONNECTION.select(mailfolder, readonly=True)
        if folder_state[0]=='OK':
            logging.info("Opened folder %s which contains %s mails", mailfolder, folder_state[1][0])
            for uid in getUIDs(mailfolder):
                mail = LazyMail(uid)
                #Do not download the mail again, if you already have it in an previous run
                if not mail.getHashcode() in DATABASE:
                    if saveMailToHardDisk(mail):
                        addHashCodeToDatabase(mail.getHashcode())
                        STATS_ADDED_EMAILS+=1
                    else:
                        logging.error("Failed to save mail with hashcode %s", mail.getHashcode())
                        STATS_FAILED_EMAILS+=1
                      
            MAIL_CONNECTION.close()
            logging.info("Closed folder %s", mailfolder)
        else:
            logging.error("Could not connect to mailbox %s because of %s", mailfolder, folder_state)
        
    except Exception as e:
        STATS_FAILED_FOLDERS+=1
        logging.error("Failed to process mailbox %s because of %s",mailfolder, e)

#close the database file, so that all new hashcodes are saved
DATABASE_FILE.close()
#close the connection to the server
# (would be closed automatically after some time, but if there are too
#  many open connections, we maybe cannot login for some time)
MAIL_CONNECTION.logout()
logging.info("Closed connection to server")


#Stats
print ""
print "==STATS=========================================="
print STATS_EMAIL_IN_DATABASE, " emails in database"
print STATS_ADDED_EMAILS, " new emails downloaded"
print STATS_ADDED_ATTACHMENTS, " new attachments downloaded"
print STATS_FAILED_FOLDERS, " folders failed to download"
print STATS_FAILED_EMAILS, " mails failed to download"
print STATS_FAILED_ATTACHMENTS, " attachments failed to download"

