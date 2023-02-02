## CrayXD_PFUT
### Pre-requistes
Refer to pre_requistes.txt file for the list of modules and dependencies version and download links.
### Database Create
Run database_update.py file along with input file if any to create pysqlitecipher.db if no input file is passed as argument to be imported 
<br>prompts to input IP and its credentials are given .The -f flag is used for updating database with input file. If the database is created 
<br>already, run the same command with the existing password to update the entries in database or append new entries or delete entries. Currently there are 
<br>no options to update database password. The IP and its credentials are encrypted in the database. The format of input file to be 
<br>imported is same as the input file mentioned in the below Input details section. 
### Input details
The Input file can be a .csv or .txt file, the default file for input is list.txt. list.txt can have IP/hostname,Username and password 
<br>seperated by ";" or only the list of IP Address the Credentials for the same can be passed as prompts using -t promptall or extracted
<br>from database after creation
<br>Eg: IP;username;Password
<br>"#" can be used to comment line in .txt file Custom file can be sent a input by mentioning the filename -f flag while invoking the main python file. In case of .csv file to be sent as input file, The column names are IP,User and Password.The IP can be selected individually also using -t flag
<br>Eg: -t IP,User,Password 
<br>Eg: -t IP,prompt ---> Prompts for Username and Password
<br>Eg: -t prompt ---> Prompts for IP,Username and Password
<br>Eg: -t promptall ---> Prompts for Username and Password in input file
<br>To select credentials from the database, choose db mode, the tool scans IP in the input file and accesses the credentials from database when correct database password is passed as the prompt
<br>Eg:	-db flag for Database.
### Report details
Reports will generated and displayed on the shell, copy of csv file will be loaded in /report directory.
<br>-d flag can be used for Node discovery report which has IP Address, Host Name and Server Model. 
<br>-i flag can be used for Node Inventory report which has IP Address, Host Name, Server Model, BMC Version and BIOS Version.
<br>-a for can be used to obtain all Firmware details.
### Update details
 FirmwareToDeploy.txt is file consisting details of server model, firmware type, version and file name seperated by ";" to be updated.
<br>Eg: HPE Cray XD220v;BIOS;00.81.0000;CU2K_5.27_v0.81_07142022_signed.bin.hpm
<br>-z can be used for update the component chosed with -c where we pass BMC(Case insensitive) and BIOS(Case insensitive) for update, if 
<br>-c not passed as argument,prompt to select component is given. -F forces installs when the version to be updated is same as the version,
<br>otherwise the update is skipped. -P PowerCycles the setup when required,Currently AC Power Cycling is required for BIOS update, if -P
<br>flag is not passed for Bios Update then, AC Power Cycling will be skipped.
