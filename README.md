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

The source is published with GPLv3.
