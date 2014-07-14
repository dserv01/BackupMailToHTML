BackupMailToHTML
=================

Why do you need it?
-------------------

Most Mail-Servers do not have differential backup, meaning if you accidentally delete an e-mail, you maybe have no chance to get it back.
A more serious problem is, that a software-failure deletes some mails.
I lost once my whole mail archive due to an unknown reason and I did no backups of them since Thunderbird saves all mails into one file and during every backup, all my mails would be uploaded to the backup-server.
I searched for mail backup tools, but all tools I found had some shortcomings.
The best one I found was https://github.com/RaymiiOrg/NoPriv, which I first forked but then wrote a new base app, which only uses parts of NoPriv.
However, NoPriv is more for actually browsing your backup and takes account of folders.
With my mail server, each folder change resulted in a new backup of the folder.
This is a horror for differential backups and I also wanted once downloaded mails never to change again.
Actually reading the mails is only necessary for the case of data loss and therefore a folder structure or sorting is not necessary.
The downloaded messages however should be readable without any special tool to validate the success.

What can it do?
---------------

BackupMailToHTML will save every mail into a single HTML-file. Attachments are downloaded too and linked within the HTML.
The folder-structure is date (of retrieval) dependant but not mailbox dependent.
As the IMAP-Protocol does not offer global unique ids, their headers will be hashed and used as ID.
The mails are saved under this ID and will never be deleted by the tool itself.
This makes it possible to save even mails of different accounts into the same folder or merge two backups of the same.
For keeping the traffic low, this hash value is also used for checking if a mail has already been downloaded.
As the data needed to be downloaded for hashing is usually around 4KB, you can check 10.000 mails with only 40MB of traffic.

** This Tool will only read your Mail-Account but never change it. It will only connect in *READ ONLY* mode **

Get it!
---------
Simple execute in the destination directory:
<pre>
git pull https://github.com/dserv01/BackupMailToHTML.git
</pre>
Please remember that git will create a new folder 'BackupMailToHTML' and put the files into it.
However you can move the files anywhere you want.
The important files are backupMailToHTML.py (Script) and config.ini (Example Configuration).

Configure it!
---------
The configuration is done with an .ini-file.
You can have multiple different configurations, if you want to back up multiple accounts.
If you want to use a configuration with a different name or path than use the path to this file as parameter.

The ini-file has following structure:
<pre>
[mail]
imap_server = imap.mail.com
imap_user = name@mail.com
imap_password = password123
#imap_port = 1337

[backup]
database_file = ./database.db
backup_folder = ./backup-mail/
</pre>
Simply change it as you like.
Do only uncomment imap_port if you define it!

The database_file is the file, where the hashcodes are saved.
backup_folder is the folder, where the emails will be saved.

Use it!
--------

Simple execute for the configuration you want to execute:
<pre>
./backupMailToHTML mymailconfig.ini
</pre>
or if you use the 'config.ini' simply
<pre>
./backupMailToHTML
</pre>
If Linux does not want to execute it, execute 
<pre>
chmod +x ./backupMailToHTML
</pre>

If your system doesn't like Magic Line, you have to put 'python' in front of the execution.

Screenshots
-------------

![Alt text](http://dserv01.de/files/BackupMailToHTML/screenshot1.png "Downloading new Mails")
![Alt text](http://dserv01.de/files/BackupMailToHTML/screenshot2.png "A mail as HTML")
![Alt text](http://dserv01.de/files/BackupMailToHTML/screenshot3.png "Download only new Mails")

License
-------------
The source is (like NoPriv) published under the GPLv3 license.
This means you can mostly copy and use as you like.
Parts of NoPriv are used (mostly in modified form), but this project is neither linked to it nor will updates of it be considered.

It is developed for Python2.7 and only tested with Linux.
I am no Python-Expert and therefore the code may be not perfect.
