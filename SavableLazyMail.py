from LazyMail import LazyMail, encode_string
import email
import datetime
import os
import cgi
import re
import logging
from email.header import decode_header

__author__ = 'doms'


class SavableLazyMail(LazyMail):
    def __init__(self, config, mail_connection, uid):
        self.CONFIG = config
        LazyMail.__init__(self, mail_connection, uid)

    #Gets a LazyMail and saves it to disk
    #It will use the Hashcode as Filename and the date as path
    #The Date-Path can be configured
    #Returns true if successful. If it returns false there was at least a little failure. No rollback is made
    def saveMailToHardDisk(self):
        #Getting path from date
        parsed_mail = self.getParsedMail()
        date_raw = email.utils.parsedate_tz(parsed_mail['Date'])
        if date_raw:
            local_date_raw = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_raw))
            path = local_date_raw.strftime(self.CONFIG.FOLDER_SYSTEM)
        else:
            path = "NoDate/"

        #Save to file
        try:
            #Create Path if not exist
            mail_folder_path = os.path.join(self.CONFIG.BACKUP_FOLDER_PATH, path)
            if not os.path.exists(mail_folder_path):
                os.makedirs(mail_folder_path)

            #save eml file which can be opened with thunderbird (is more or less what the server has returned)
            if self.CONFIG.SAVE_EML:
                eml_path = os.path.join(mail_folder_path, "eml", )
                if not os.path.exists(eml_path):
                    os.makedirs(eml_path)
                self.saveEMLtoFile(eml_path)

            #Save attachments: If there are none, False will be returned
            check_attachments, attachments = self.saveAttachmentsToHardDisk(mail_folder_path)

            #Create HTML-File
            full_path = os.path.join(mail_folder_path, self.getHashcode()) + ".html"
            file_message_without_attachment = open(full_path, 'w')
            check_html = self.writeToHTML(attachments, file_message_without_attachment)
            file_message_without_attachment.close()

        except Exception as e:
            #If anything has failed
            logging.error("Failed to save mail (%s,%s) because of %s", self.getDate(), self.getSubject(), e)
            return False

        if check_attachments and check_html:
            logging.info("Saved mail (From: %s, Subject: %s) to %s", self.getFrom(), self.getSubject(), full_path)
            return True
        elif check_attachments or check_html:
            logging.info("Partly saved mail (From: %s, Subject: %s) to %s", self.getFrom(), self.getSubject(), full_path)
            return False
        else:
            logging.info("Could not save mail (From: %s, Subject: %s)", self.getFrom(), self.getSubject())
            return False


    #Writes a lazy_mail to a given HTML-File
    def writeToHTML(self, attachments, html_file):
        check = True
        try:
            #HTML-Header
            html_file.write("<!DOCTYPE html> <html lang=\"en\"> <head> <title>")
            html_file.write(self.getSubject())
            html_file.write("</title> <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"> </head> <body> <div class=\"row\"> <div class=\"col-md-12\">")

            #HTML-Table with To,From,Subject
            html_file.write("<table boarder=\"1\">\n")
            html_file.write("\t<tr>\n")
            html_file.write("\t\t<td>From: </td>\n")
            html_file.write("\t\t<td>" + self.getFrom() + "</td>\n")
            html_file.write("\t<tr>\n")

            html_file.write("\t<tr>\n")
            html_file.write("\t\t<td>To: </td>\n")
            html_file.write("\t\t<td>" + self.getTo() + "</td>\n")
            html_file.write("\t<tr>\n")

            html_file.write("\t<tr>\n")
            html_file.write("\t\t<td>Subject: </td>\n")
            html_file.write("\t\t<td>" + self.getSubject() + "</td>\n")
            html_file.write("\t<tr>\n")

            html_file.write("\t<tr>\n")
            html_file.write("\t\t<td>Date: </td>\n")
            html_file.write("\t\t<td>" + self.getDate() + "</td>\n")
            html_file.write("\t<tr>\n")

            #Information in Table if Attachments
            if len(attachments) > 0:
                html_file.write("\t<tr>\n")
                html_file.write("\t\t<td>Attachments: </td><td>")
                for attachment in attachments:
                    html_file.write("<a href=\"" + attachment[0] + "\">" + cgi.escape(encode_string(str(attachment[1]), None)) + "</a>")
                    if attachment is not attachments[-1]:
                        html_file.write(", ")
                html_file.write("</td>\n")
                html_file.write("\t<tr>\n")

            html_file.write("</table>\n")
            html_file.write("<div class=\"col-md-8 col-md-offset-1 footer\"> <hr /><div style=\"white-space: pre-wrap;\">")
            #Write content to File
            check, content_of_mail = self.getContent()
            if content_of_mail['text']:
                html_file.write("<pre>")
                strip_header = re.sub(r"(?i)<html>.*?<head>.*?</head>.*?<body>", "", content_of_mail['text'],
                                  flags=re.DOTALL)
                strip_header = re.sub(r"(?i)</body>.*?</html>", "", strip_header, flags=re.DOTALL)
                strip_header = re.sub(r"(?i)<!DOCTYPE.*?>", "", strip_header, flags=re.DOTALL)
                strip_header = re.sub(r"(?i)POSITION: absolute;", "", strip_header, flags=re.DOTALL)
                strip_header = re.sub(r"(?i)TOP: .*?;", "", strip_header, flags=re.DOTALL)
                html_file.write(strip_header)
                html_file.write("</pre>\n")

            if content_of_mail['html']:
                strip_header = re.sub(r"(?i)<html>.*?<head>.*?</head>.*?<body>", "", content_of_mail['html'],
                                  flags=re.DOTALL)
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
            logging.error("Could not write HTML because of %s", e)
            raise e

        return check


    #Saves the attachments of a LazyMail to disk. Uses the Path 'folder_prefix-filename'
    #E.g for folder_prefix="2014/05/03/4a9fd924" and filename="photo.jpg" it will be "2014/05/03/4a9fd924-photo.jpg"
    def saveAttachmentsToHardDisk(self, folder):
        attachments_tuple_for_html = []
        filename_count = dict()  #to handle attachments with same name
        successful = True
        for part in self.getParsedMail().walk():
            attachment_filename = "(Could not encode)"
            attachment_filename_encoding = None

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
                    logging.debug("Workaround Filename Encoding")
                    logging.debug(str(part))
                    try:
                        attachment_filename = encode_string(part.get_filename(), None)  #"(could not encode filename)"
                        logging.debug(attachment_filename)
                    except:
                        logging.error("Could not encode filename, %s", e)
                        attachment_filename = "(Could not encode)"
                        attachment_filename_encoding = None
                        successful = False

                if not attachment_filename:
                    logging.warning("Empty part in mail. Don't know what to do with it!")
                    logging.debug(str(part))
                    continue

                #put a (x) behind filename if same filename already exists
                if attachment_filename in filename_count:
                    filename_count[attachment_filename] = filename_count[attachment_filename] + 1
                    logging.debug("Same Filename %s", attachment_filename)
                    root, ext = os.path.splitext(attachment_filename)
                    attachment_filename = root + "(" + str(filename_count[attachment_filename]) + ")" + ext

                else:
                    filename_count[attachment_filename] = 1

                attachment_folder_name = os.path.join("attachments", self.getHashcode(), "")
                attachment_folder_path = os.path.join(folder, attachment_folder_name)
                attachments_tuple_for_html += [(attachment_folder_name + attachment_filename, cgi.escape(
                    encode_string(attachment_filename, attachment_filename_encoding)))]  #TODO

                if not os.path.exists(attachment_folder_path):
                    os.makedirs(attachment_folder_path)

                attachment_path = attachment_folder_path + attachment_filename

                attachment_file_disk = open(attachment_path, "wb")
                attachment_file_disk.write(part.get_payload(decode=True))
                logging.info("Saved attachment %s to %s", attachment_filename, attachment_path)
                #global STATS_ADDED_ATTACHMENTS TODO
                #STATS_ADDED_ATTACHMENTS += 1 TODO
            except Exception as e:
                successful = False
                #global STATS_FAILED_ATTACHMENTS TODO
                #STATS_FAILED_ATTACHMENTS += 1 TODO
                logging.error("Failed to save attachment %s: %s", attachment_filename, e)

        return successful, attachments_tuple_for_html