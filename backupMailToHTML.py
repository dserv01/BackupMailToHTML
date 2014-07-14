#!/usr/bin/env python

import sys
import imaplib
import getpass
import email
import datetime
import hashlib
import os
import cgi
import re
import ConfigParser
from email.header import decode_header

#Configuration
FOLDER_SYSTEM = "%Y/%m/%d/" #%H/%M/"
DATABASE_FILE_PATH =None
BACKUP_FOLDER_PATH =None
MAIL_SERVER=None
MAIL_USER=None 
MAIL_PASSWORD=None 
MAIL_PORT=None

#Load Configuration from ini
CONFIG = ConfigParser.RawConfigParser()
try:
    if len(sys.argv)>1 and os.path.isfile(sys.argv[1]):
        CONFIG.read(sys.argv[1])
        print "Loaded configuration: ", sys.argv[1]
    else:
        CONFIG.read("./config.ini")
except Exception as e:
    print "Could not load Configuration: ",e
    exit(1)

try:
    MAIL_SERVER = CONFIG.get('mail', 'imap_server')
    MAIL_USER = CONFIG.get('mail', 'imap_user')
    MAIL_PASSWORD= CONFIG.get('mail', 'imap_password')
    DATABASE_FILE_PATH = CONFIG.get('backup','database_file')
    BACKUP_FOLDER_PATH = CONFIG.get('backup','backup_folder')
except Exception as e:
    print "Could not load parameters"
    print e
    print "You need to define a config.ini which could look as follows:"
    print "[pymail]"
    print "imap_server = imap.mail.com"
    print "imap_user = misterx@mail.com"
    print "imap_password =secretpassword123"
    print "database_file = database.db"
    print "backup_folder = ./backup"
    print ""
    print "You can also pass the ini by parameter and give it another name as config.ini"
    print "You can also define imap_port to get another port"

try:
    MAIL_PORT = CONFIG.get('pymail', 'imap_port')
except:
    MAIL_PORT = None #Default

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
    print "Created New Database ",DATABASE_FILE_PATH

print "Load Database..."
for line in DATABASE_FILE:
    DATABASE.add(line.replace('\n',''))
print "Loaded ",len(DATABASE)," Entries"
STATS_EMAIL_IN_DATABASE = len(DATABASE)
DATABASE_FILE.close()
#Open Database-File for appending new HashCodes
DATABASE_FILE = open(DATABASE_FILE_PATH, 'a') 


#Init Mail Connection
MAIL_CONNECTION = imaplib.IMAP4_SSL(MAIL_SERVER, MAIL_PORT) if MAIL_PORT else imaplib.IMAP4_SSL(MAIL_SERVER) 
try:
    MAIL_CONNECTION.login(MAIL_USER,MAIL_PASSWORD)
except imaplib.IMAP4.error as e:
    print "Could not Log in: ",e
    print "User: ", MAIL_USER
    print "Password: ", MAIL_PASSWORD
    exit()

#fetches the mailboxes/mailfolders lik "INBOX", "INBOX.Archives.2011" ('.' is separator)
# and gives it back as List
def fetchMailFolders():
    check, mailfolders_raw = MAIL_CONNECTION.list()
    mailfolders_parsed = []
    if check == 'OK':
        for folder_information in mailfolders_raw:
            #folder_information looks for example like:
            # (\HasNoChildren \UnMarked) "." "INBOX.Archives.2011"
            folder_name = folder_information.split()[-1].replace('\"', '')
            mailfolders_parsed.append(folder_name)
    else:
        print "Error in looking up folders"
    return mailfolders_parsed

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
            print 'Could not fetch mail header ',self.__uid

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
            print "Fetch complete mail..."
            check, maildata_raw = MAIL_CONNECTION.uid("FETCH", self.__uid, '(RFC822)')
            if check == 'OK':
                self.__parsedMail = email.message_from_string(maildata_raw[0][1])
            else:
                print 'Could not fetch mail ', self.__uid

        return self.__parsedMail

    #Returns the well formated 'from'
    def getFrom(self):
        if not self.__from:
            mail_from = email.utils.parseaddr(self.getParsedMail().get('From'))[1]
            mail_from_encoding = decode_header(self.getParsedMail().get('From'))[0][1]
            if not mail_from_encoding:
                mail_from_encoding = "utf-8"

            self.__from = cgi.escape(unicode(mail_from, mail_from_encoding)).encode('ascii', 'xmlcharrefreplace')

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

            self.__subject = cgi.escape(unicode(mail_subject, mail_subject_encoding)).encode('ascii', 'xmlcharrefreplace')

        return self.__subject

    #returns the well formated 'to'
    def getTo(self):
        if not self.__to:
            mail_to = email.utils.parseaddr(self.getParsedMail().get('To'))[1]
            mail_to_encoding = decode_header(self.getParsedMail().get('To'))[0][1]
            if not mail_to_encoding:
                mail_to_encoding = "utf-8"

            self.__to = cgi.escape(unicode(mail_to, mail_to_encoding)).encode('ascii', 'xmlcharrefreplace')

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

        for part in self.getParsedMail().walk():
            part_content_type = part.get_content_type()
            part_charset = part.get_charsets()
            if part_content_type == 'text/plain':
                part_decoded_contents = part.get_payload(decode=True)
                try:
                    if part_charset[0]:
                        content_of_mail['text'] += cgi.escape(unicode(str(part_decoded_contents), part_charset[0])).encode('ascii', 'xmlcharrefreplace')
                    else:
                        content_of_mail['text'] += cgi.escape(str(part_decoded_contents)).encode('ascii', 'xmlcharrefreplace')
                except Exception:
                    content_of_mail['text'] += "Error decoding mail contents."
                    print("Error decoding mail contents")

                continue
            elif part_content_type == 'text/html':
                part_decoded_contents = part.get_payload(decode=True)
                try:
                    if part_charset[0]:
                        content_of_mail['html'] += unicode(str(part_decoded_contents), part_charset[0]).encode('ascii', 'xmlcharrefreplace')
                    else:
                        content_of_mail['html'] += str(part_decoded_contents).encode('ascii', 'xmlcharrefreplace')
                except Exception:
                    content_of_mail['html'] += "Error decoding mail contents."
                    print("Error decoding mail contents")

                continue
        return content_of_mail


#Get Mail UIDs of mail_folder (in mailfolders_parsed)
#They are only unique in mail_folder and session!
def getUIDs(mail_folder):
    check, uids_raw = MAIL_CONNECTION.uid('SEARCH', None, "ALL")
    if check == 'OK':
        MAIL_UIDs = uids_raw[0].split()
        return MAIL_UIDs
    else:
        print "Error in fetching UIDs for folder", mail_folder
        return []


#adds a hashcode of a mail to the database such that it won't be fetched
# another time with all its attachments and co
# the hashcode is generated by getHashcode(uid)
def addHashCodeToDatabase(hashcode):
    DATABASE_FILE.write(hashcode+"\n") #The \n has to be removed by reading
    DATABASE.add(hashcode)
    print "Added ",hashcode
    global STATS_EMAIL_IN_DATABASE
    STATS_EMAIL_IN_DATABASE +=1



#Gets a LazyMail and saves it to disk
#It will use the Hashcode as Filename and the date as path
#The Date-Path can be configured
#Returns true if successful. If it returns false there was at least a little failure. No rollback is made
def saveMailToHardDisk(lazy_mail):
    print " Saving Mail: ",lazy_mail.getFrom(), ">",lazy_mail.getSubject()

    #Getting path from date
    parsed_mail = lazy_mail.getParsedMail()
    date_raw = email.utils.parsedate_tz(parsed_mail['Date'])
    if date_raw:
        local_date_raw = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_raw))
        path = local_date_raw.strftime(FOLDER_SYSTEM)
        print path
    else:
        path = "NoDate/"

    #Save to file
    try:
        #Create Path if not exist
        mail_folder_path = os.path.join(BACKUP_FOLDER_PATH,path)
        if not os.path.exists(mail_folder_path):
            os.makedirs(mail_folder_path)

        #Save attachments: If there are no, False will be returned
        attachments = saveAttachmentsToHardDisk(parsed_mail, os.path.join(mail_folder_path,lazy_mail.getHashcode()))

        #Create HTML-File
        file_message_without_attachment = open(os.path.join(mail_folder_path,lazy_mail.getHashcode())+".html", 'w')
        writeToHTML(lazy_mail, attachments, file_message_without_attachment)
        file_message_without_attachment.close()

    except Exception as e:
        #If anything has failed
        print "Could not write file: ",e
        return False
    return True



#Writes a lazy_mail to a given HTML-File
def writeToHTML(lazy_mail, attachments, html_file):
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
                html_file.write("<a href=\""+lazy_mail.getHashcode()+"-"+attachment+"\">"+attachment+"</a>")
                if attachment is not attachments[-1]:
                    html_file.write(", ")
            html_file.write("</td>\n")
            html_file.write("\t<tr>\n")
    
        html_file.write("</table>\n")
        html_file.write("<div class=\"col-md-8 col-md-offset-1 footer\"> <hr /><div style=\"white-space: pre-wrap;\">")
        #Write content to File
        content_of_mail = lazy_mail.getContent()
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
        html_file.write("</div> <div class=\"col-md-8 col-md-offset-1 footer\"> <hr /><div style=\"white-space: pre-wrap;\">")
        html_file.write(lazy_mail.getHeader())
        html_file.write("</div></div></body></html>")

    except Exception as e:
        print "Could not write to HTML"

#Saves the attachments of a LazyMail to disk. Uses the Path 'folder_prefix-filename'
#E.g for folder_prefix="2014/05/03/4a9fd924" and filename="photo.jpg" it will be "2014/05/03/4a9fd924-photo.jpg"
def saveAttachmentsToHardDisk(mail, folder_prefix):
    attachments_filenames = []
    for part in mail.walk():
        content_maintype = part.get_content_maintype()
        if content_maintype == 'multipart' or content_maintype == 'text' or content_maintype == 'html':
            continue

        if part.get('Content-Disposition') == None:
            continue
        
        attachment_name = part.get_filename()
        if not attachment_name:
            print "Empty Part in E-Mail!"
            print str(part)
            continue
        attachments_filenames += [attachment_name]
        attachment_path = folder_prefix+"-"+attachment_name
       
        try:
            attachment_file_disk = open(attachment_path, "wb")
            attachment_file_disk.write(part.get_payload(decode=True))
            print "Saved attachment ", attachment_path
            global STATS_ADDED_ATTACHMENTS
            STATS_ADDED_ATTACHMENTS += 1
        except Exception as e:
            global STATS_FAILED_ATTACHMENTS
            STATS_FAILED_ATTACHMENTS+=1
            print "Failed to save attachment "+attachment_path
            print e
            print part.get_filename()
            raise e #TODO Create new Exception

    return attachments_filenames


#goes through all folders and checks the emails
for mailfolder in fetchMailFolders():
    print "Go through folder ",mailfolder
    try:
        MAIL_CONNECTION.select(mailfolder, readonly=True)
        for uid in getUIDs(mailfolder):
            mail = LazyMail(uid)
            #Do not download the mail again, if you already have it in an previous run
            if not mail.getHashcode() in DATABASE:
                if saveMailToHardDisk(mail):
                    addHashCodeToDatabase(mail.getHashcode())
                    STATS_ADDED_EMAILS+=1
                else:
                    print "Failed to save ", mail.getHashcode()
                    STATS_FAILED_EMAILS+=1

        MAIL_CONNECTION.close()
    except Exception as e:
        STATS_FAILED_FOLDERS+=1
        print "Could not download folder ",mailfolder
        print e
        print "This can happen if the folder is empty or not correct created/deleted"



#close the database file, so that all new hashcodes are saved
DATABASE_FILE.close()
#close the connection to the server
# (would be closed automatically after some time, but if there are too
#  many open connections, we maybe cannot login for some time)
MAIL_CONNECTION.logout()


#Stats
print ""
print "==STATS=========================================="
print STATS_EMAIL_IN_DATABASE, " emails in database"
print STATS_ADDED_EMAILS, " new emails downloaded"
print STATS_ADDED_ATTACHMENTS, " new attachments downloaded"
print STATS_FAILED_FOLDERS, " folders failed to download"
print STATS_FAILED_EMAILS, " mails failed to download"
print STATS_FAILED_ATTACHMENTS, " attachments failed to download"

