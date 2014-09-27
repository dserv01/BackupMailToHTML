__author__ = 'doms'

import email
import hashlib
import os
import cgi
import logging
from email.header import decode_header

def encode_string(string, encoding):
    try:
        if encoding:
            return unicode(string, encoding).encode('ascii', 'xmlcharrefreplace')
        else:
            return unicode(string).encode('ascii', 'xmlcharrefreplace')
    except Exception as e:
        logging.warning("Encoding failed: Trying brute force encoding (should work) - %s", str(e))
        for charset in ("utf-8", 'latin-1', 'iso-8859-1', 'us-ascii', 'windows-1252', 'us-ascii'):
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
    def __init__(self, mail_connection, uid):
        self.__uid = uid
        self.__fetchedHeader = None
        self.__headerhash = None
        self.__parsedMail = None
        self.__subject = None
        self.__from = None
        self.__to = None
        self.__date = None
        self.__maildataRaw = None
        self.__mailConnection = mail_connection

    #Returns a non formated or parsed header
    def getHeader(self):
        if not self.__fetchedHeader:
            #print "Fetch Header..."
            check, maildata_raw = self.__mailConnection.uid("FETCH", self.__uid, '(RFC822.HEADER)')
            if check == 'OK':
                self.__fetchedHeader = maildata_raw[0][1]
            else:
                logging.warning("Could not fetch mail header for ", self.__uid)
        return self.__fetchedHeader


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
            check, self.__maildataRaw = self.__mailConnection.uid("FETCH", self.__uid, '(RFC822)')
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
                self.__from = cgi.escape(encode_string(mail_from, mail_from_encoding))
            except Exception as e:
                logging.warning("Could not decode 'from' because of %s", e)
                self.__from = "(Could not decode)"
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
                self.__subject = cgi.escape(encode_string(mail_subject, mail_subject_encoding))
            except Exception as e:
                logging.warning("Could not decode subject because of %s", e)
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
                self.__to = cgi.escape(encode_string(mail_to, mail_to_encoding))
            except Exception as e:
                logging.warning("Could not decode 'to' because of %s", e)
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
                    content_of_mail['text'] += cgi.escape(encode_string(str(part_decoded_contents), part_charset[0]))
                except Exception as e:
                    content_of_mail['text'] += "Error decoding mail contents."
                    logging.error("Could not decode text content of mail (%s,%s) because of %s", self.getDate(),
                                  self.getSubject(), e)
                    check = False

                continue
            elif part_content_type == 'text/html':
                part_decoded_contents = part.get_payload(decode=True)
                try:
                    content_of_mail['html'] += encode_string(str(part_decoded_contents), part_charset[0])
                except Exception as e:
                    content_of_mail['html'] += "Error decoding mail contents."
                    logging.error("Could not decode html content of mail (%s,%s) because of %s", self.getDate(),
                                  self.getSubject(), e)
                    check = False

                continue
        return check, content_of_mail

    def getBaseFilename(self):
        return self.getHashcode()

    def saveEMLtoFile(self, folder_path):
        full_path = os.path.join(folder_path, self.getBaseFilename() + ".eml")
        emlfile = open(full_path, 'w')
        emlfile.write(self.getRawMaildata()[0][1])
        emlfile.close()
        logging.debug("Saved EML %s", full_path)
