from pysqlitecipher import sqlitewrapper
import getpass
import traceback
import argparse
import sys
import pandas as pd

def file_processing(filename, operation):
    ipList = {}
    del_list = []
    ip = ""
    if filename.endswith ('.txt'):
        fp = open(filename, 'r')
        lines = fp.readlines()
        for line in lines:
            iscomment = line.startswith('#')
            if not iscomment and line.strip() != "":
                ip_row = line.rstrip('\n')
                if ";" in ip_row:
                    ip_split = ip_row.split(';')
                    if len(ip_split) > 2 :
                        ip = ip_split[0]
                        if ip=="":
                            print("INFO: IP_HostName_FQDN is missing in line %s" % line)
                            continue
                        if operation == "add":
                            username = ip_split[1]
                            password = ip_split[2]
                            if(username != "" and password != ""):
                                ip_list[ip] = {}
                                ip_list[ip]["username"] = username
                                ip_list[ip]["password"] = password
                            else:
                                print("INFO: For " + ip_split[0] + " ';' is added in the input file and either Username or Password or both is not mentioned use --help for more info")
                        else:
                            del_list.append(ip)
                    elif len(ip_split)==2:
                        ip = ip_split[0]
                        if ip == "":
                            print("INFO: IP_HostName_FQDN is missing in line %s"%line)
                            continue
                        if operation == "add":
                            print("INFO: For " + ip_split[0] + " ';' is added in the input file and either Username or Password or both is not mentioned use --help for more info")
                        elif operation == "delete":
                            del_list.append(ip)
                    else:
                        print("INFO: For " + ip_split[0] + " ';' is added in the input file and either Username or Password or both is not mentioned use --help for more info")
                else:
                    ip = ip_row
                    if operation == "add":
                        print("INFO: For "+ip+" has missing Username or Password or both in the input file use --help for more info")
                    elif operation == "delete":
                        del_list.append(ip)

        fp.close #fp.close()
    elif filename.endswith ('.csv'):
        data = pd.read_csv(filename)
        length_framework = len(data)
        if operation == "add":
            if 'Username' in data.columns and 'Password' in data.columns and 'IP_HostName_FQDN' in data.columns:
                for i in range (0,length_framework) :
                    ip = data.IP_HostName_FQDN[i]
                    if ip=="":
                        continue
                    if(pd.isna(data.Username[i]) or pd.isna(data.Password[i]) ): #username or password any is empty!!
                        print( "INFO: "+ip+" has missing Username or Password or both in .csv file")
                    else: #if both are not empty
                        ip_list[ip] = {}
                        ip_list[ip]["username"] = data.Username[i]
                        ip_list[ip]["password"] = data.Password[i]
            else:
                print("ERROR: Invalid column names IP_HostName_FQDN,Username,Password are column names")
        elif operation == "delete":
            if 'IP_HostName_FQDN' in data.columns:
                for i in range(0,length_framework):
                    ip = data.IP_HostName_FQDN[i]
                    if ip=="":
                        continue
                    else:
                        del_list.append(ip)

    else:
        print("ERROR: Only csv file or txt file can be processed")
    if operation=="add":
        return ip_list
    elif operation == "delete":
        return del_list
    

existingIPEntries = []
ip_list = {}
toprompt = []
tableName = "IP_List_Details"
colList = [["IP_HostName_FQDNs","TEXT"],["Username","TEXT"],["Password","TEXT"]]

parser = argparse.ArgumentParser(description="",formatter_class=argparse.RawTextHelpFormatter)
parser.version = '1.1'

parser.add_argument('-f','--filename', action='store', help='''Text file from 
1. which IP_HostName_FQDNs and the credentials are to be added to the database if \"Add\" is selected
2. which IP_HostName_FQDNs are to be deleted from the database if \"Delete\" is selected''')

parser.add_argument('-o','--operation',action='store',help='''Multiple operations.
1. -o add - Update the database with IP_HostName_FQDNs entries
2. -o delete - Delete IP_HostName_FQDNs entries from the database
3. -o view - View IP_HostName_FQDNs entries in the database''')

args = parser.parse_args()
operation = ""

if not args.operation:
    print("Enter the operation to be performed on the database, Choose A/a or B/b or C/c" )
    operation = input("A)Add B)Delete C)View \n").lower()
    if operation!='a' and operation!='b' and operation!='c':
        print("ERROR: Invalid operation chosen... exiting")
        sys.exit()
    if operation=="a":
        args.operation = "add"
    elif operation=="b":
        args.operation = "delete"
    else:
        args.operation ="view"

if args.operation.lower()!="add" and args.operation.lower()!="delete" and args.operation.lower()!="view":
    print("ERROR: Invalid operation chosen... exiting")
    sys.exit()
elif args.operation.lower()=="view" and args.filename:
    print("ERROR: Invalid Input... exiting\n INFO: VIEW operation does not need any input file.. Please try without giving file input to perform \"View\" operation")
    sys.exit()
else:
    args.operation = args.operation.lower()

print("Please enter the database password")
database=getpass.getpass()

try:
    obj = sqlitewrapper.SqliteCipher(dataBasePath="pysqlitecipher.db" , checkSameThread=False , password=database)
    try:
        #table doesn't exist, creating a new one
        obj.createTable(tableName, colList, makeSecure=True, commit=True)
    except:
        if args.operation!="add":
            print("\nINFO: Table already exists")
        else:
            print("\nINFO: Table already exists, appending the data if any")
        pass
    updated_credentials = []
    existingTableEntries = obj.getDataFromTable(tableName , raiseConversionError = True , omitID = False)[1] #[[0,"IP1","u1","p1"],[1,"IP2","u2","p2"],[2,"IP3","u3","p3"]]
    existingIPEntries = []
    for entry in existingTableEntries:
        existingIPEntries.append(entry[1])
    if existingIPEntries != [] and args.operation!="view":
        print()
        print("INFO: Before performing any database operation, IP_HostName_FQDNs entries in database are ", end="")
        print(*existingIPEntries,sep=", ")
        print()
    if existingIPEntries == []:
        print("INFO: Before performing any database operation, Database is empty!!")
    while True and args.operation=="add":
        if not args.filename:
            print("Enter IP_HostName_FQDNs to be added/updated to the database or Enter 'q' to quit")
            ip = input()
            if ip.lower() =='q':
                break
            if ip=="":
                print("WARNING: IP_HostName_FQDNs cannot be empty.")
                continue
            if ip not in existingIPEntries:
                username = input("Enter %s Username: " %ip)
                password = getpass.getpass("Enter %s Password: " %ip)
                if username !="" and password != "":
                    insertList = [ip,username,password] 
                    obj.insertIntoTable(tableName, insertList, commit = True)
                else:
                    print("WARNING: Missing credentials for "+ ip +", and so will not be appended to database")
            else:
                print("INFO: Given "+ip+" is already in the database and will be updated with the following given latest credentials.")
                username = input("Enter %s Username: " %ip)
                password = getpass.getpass("Enter %s Password: " %ip)
                if username !="" and password != "":
                    obj.updateInTable(tableName, existingIPEntries.index(ip), "Username", username, commit = True, raiseError = True)
                    obj.updateInTable(tableName, existingIPEntries.index(ip), "Password", password, commit = True, raiseError = True)
                    updated_credentials.append(ip)
                else:
                    print("WARNING: Missing Credentials Username or Password for "+ip + " , and so will not be updated in database")
        else:
            filename = args.filename
            ip_list = file_processing(filename,"add")
            for ip in ip_list:
                if ip not in existingIPEntries:
                    username = ip_list[ip]["username"]
                    password = ip_list[ip]["password"]
                    insertList = [ip,username,password] 
                    obj.insertIntoTable(tableName, insertList, commit = True)
                else:
                    print("INFO: Given "+ip+" is already in the database and will be updated with the latest credentials provided in input file.")
                    username = ip_list[ip]["username"]
                    password = ip_list[ip]["password"]
                    obj.updateInTable(tableName, existingIPEntries.index(ip), "Username", username, commit = True, raiseError = True)
                    obj.updateInTable(tableName, existingIPEntries.index(ip), "Password", password, commit = True, raiseError = True)
                    updated_credentials.append(ip)

            break
        existingTableEntries = obj.getDataFromTable(tableName , raiseConversionError = True , omitID = False)[1] #[[0,"IP1","u1","p1"],[1,"IP2","u2","p2"],[2,"IP3","u3","p3"]]
        existingIPEntries = []
        for entry in existingTableEntries:
            existingIPEntries.append(entry[1])
    existingTableEntries = obj.getDataFromTable(tableName , raiseConversionError = True , omitID = False)[1] #[[0,"IP1","u1","p1"],[1,"IP2","u2","p2"],[2,"IP3","u3","p3"]]
    existingIPEntries = []
    for entry in existingTableEntries:
        existingIPEntries.append(entry[1])
    if len(updated_credentials)>0:
        print("\nINFO: The credentials of the following IP_HostName_FQDNs were updated successfully in the database: ",end="")
        print(*updated_credentials,sep=", ")
    if existingIPEntries != []:
        deleted_ips = []
        failed_to_delete_ips = []
        while True and args.operation=="delete":
            table_entries = obj.getDataFromTable(tableName , raiseConversionError = True , omitID = False)[1]
            if not args.filename:
                ip = input("Enter the IP_HostName_FQDNs to be deleted or Enter 'q' to quit: ")
                if ip.lower()=="q":
                    break
                else:
                    try:
                        obj.deleteDataInTable(tableName, existingIPEntries.index(ip), commit = True , raiseError = True , updateId = False)
                        deleted_ips.append(ip)
                    except:
                        print("WARNING: Wrong input ",ip," is given or there is no given entry in database.. Please try again")
                        if ip not in deleted_ips: failed_to_delete_ips.append(ip)
            else:
                filename = args.filename
                ip_list = file_processing(filename,"delete")
                for ip in ip_list:
                    try:
                        obj.deleteDataInTable(tableName, existingIPEntries.index(ip), commit = True , raiseError = True , updateId = False)
                        deleted_ips.append(ip)
                    except:
                        print("WARNING: Wrong input",ip,"is given or there is no given entry in database.. Please try again")
                        if ip not in deleted_ips: failed_to_delete_ips.append(ip)
                break
        if len(deleted_ips)>0:
            print("INFO: The following IP_HostName_FQDNs are deleted successfully from the database: ", end="")
            print(*deleted_ips, sep=", ")
        if len(failed_to_delete_ips)>0:
            print("WARNING: The following IP_HostName_FQDNs cannot be deleted from the database as there are no entries of these IP_HostName_FQDNs in the database: ", end="")
            print(*failed_to_delete_ips, sep=", ")
        obj.updateIDs(tableName , commit = True)
        existingTableEntries = obj.getDataFromTable(tableName , raiseConversionError = True , omitID = False)[1] #[[0,"IP1","u1","p1"],[1,"IP2","u2","p2"],[2,"IP3","u3","p3"]]
        existingIPEntries = []
        for entry in existingTableEntries:
            existingIPEntries.append(entry[1])
        if existingIPEntries != []:
            print()
            print("INFO: Final IP_HostName_FQDNs entries in database are ", end="")
            print(*existingIPEntries,sep=", ",end="")
            print()
        else:
            print("INFO: No entries in the database!!")
    else:
        print()
        print("ERROR: No entries in the database!!")
    

    
except:
    traceback.print_exc()

    

    
