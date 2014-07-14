This is a backup-tool for IMAP-Mail-accounts with SSL inspired by https://github.com/RaymiiOrg/NoPriv.
It even uses some code of it but the result is different.
Also it is less robust against unexpected content and only works for IMAP with SSL.

The main feature of this tool is, that it backups emails independent of their folders or even mail-accounts.
The problem I had with NoPriv was, that for every backup, most of the files changed.
Not only did they changed their content, they even changed their name and another email could save with the old name.
If you backup your backup-folder, going back in time becomes very ugly.
This tool uses a hashcode of the header as ID and saves it with the hashcode as filename.
Files are never deleted, meaning that you will never lose an e-mail once downloaded even if it has been deleted on the server.
Additionally the tool only downloads mails and attachments if they haven't been downloaded before.

However, if you simply want a local copy of your mails, you should use NoPriv, as it is much more beautiful. Also there are no restore options. You can browse read the mails as HTML-files and show their attachments, but not upload them to the server again, if the server has lost them.

The configuration is done with a simple ini-file.
You can have multiple ini-files, if you want to backup multiple accounts.
Simple pass the path to the config as parameter.
If you don't pass a parameter, the config is loaded from ./config.ini

I am no python expert and wrote this tool for linux with Python2.7
You can execute the tool with ./backupMailToHTML.py as a normal script, if you made it executable.

The source is published with GPLv3.
