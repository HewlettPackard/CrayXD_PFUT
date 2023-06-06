#!/usr/bin/env python3

import argparse
import pandas as pd
import os
import redfish
import sys
import getpass
from re import search
import time
import threading
from datetime import datetime
from BIOS_Wrapper import *
from BMC_Wrapper import *
from Power_Cycle import *
from pysqlitecipher import sqlitewrapper
import getpass
import re
import traceback

global IP_HostName_FQDN
IP_HostName_FQDN = dict()
global not_Done
not_Done=0
#if IP is given, HostName/FQDN are found and it is kept as {IP:HostName,FQDN} pair
#if HostName is given, IP is found and it is kept as {IP:HostName,FQDN} pair
#if FQDN is given, IP, HostName are found and it is kept as {IP:HostName,FQDN} pair
#{IP: {"HostName": 'hn', "FQDN": 'fqdn'}}

#output_Save function adds dataframe output obtained from running reports to specified filename in the folder specified
#Currently there are two folders "reports" and "update"
#reports is the directory that has Node Discovery report, Node Inventory report and All Firmware Inventory report
#update is the directory that has reports after firmware update is performed
def output_Save(filename, foldername, dataframe):
    datetimenow = datetime.now()
    modified_datetime = datetimenow.strftime("%d_%m_%Y_%H%M%S")
    csv_filename = modified_datetime + filename + ".csv"
    path = os.getcwd()
    path_final = path + "/" + foldername
    isreport = os.path.exists(path_final)
    if not isreport:
        os.makedirs(path_final)
        print("\nINFO: The new directory for storing " + foldername + " records is created!")
    dataframe.to_csv(path_final + "/" + csv_filename, index=False)
    print("\nINFO: Saved the "+csv_filename+" in "+foldername)

#time_Display function prints time and Number of nodes present
def time_Display(target_list, flag):
    datetimenow = datetime.now()
    ReportTime = datetimenow.strftime("%x %X %p")
    print(ReportTime)
    len_nodes = len(target_list)
    #print(str(len_nodes) + ' items found')
    #if -z is selected only
    if flag:
        success_count=0
        fail_count=0
        for report in target_list.values():
            status = report["Status"]
            if status=="Success":
                success_count+=1
            else: fail_count+=1
        print('INFO: '+str(len_nodes) + ' items found,',success_count,"success,",fail_count,"failure")
    else:
        print('INFO: '+str(len_nodes) + ' items found')
    print()

#session_Processing generates ip_list when session_username and session_password
def session_Processing(filename,session_username,session_password):
    ip_list = {}
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
                    ip = ip_split[0]
                    if ip=="":
                        print("WARNING: IP_HostName_FQDN missing in the line:",line)
                        continue
                    if(session_username != "" and session_password != ""):
                        ip_list[ip] = {}
                        ip_list[ip]["username"] = session_username
                        ip_list[ip]["password"] = session_password
                    if(session_username == "" and session_password != ""):
                        if len(ip_split) > 1 :
                            if ip_split[1] != "":
                                username = ip_split[1]
                                ip_list[ip] = {}
                                ip_list[ip]["username"] = username
                                ip_list[ip]["password"] = session_password
                            else:
                                print("WARNING: Username missing for "+ ip)
                    if(session_username != "" and session_password == ""):
                        if len(ip_split) > 2 :
                            if ip_split[2] != "":
                                password = ip_split[2]
                                ip_list[ip] = {}
                                ip_list[ip]["username"] = session_username
                                ip_list[ip]["password"] = password
                            else:
                                print("WARNING: Password missing for "+ ip)
                else:
                    ip = ip_row
                    if(session_username != "" and session_password != ""):
                        ip_list[ip] = {}
                        ip_list[ip]["username"] = session_username
                        ip_list[ip]["password"] = session_password
                    elif(session_username == "" ):
                        print("WARNING: Username missing for "+ip)
                    else :
                        print("WARNING: Password missing for "+ ip)

        fp.close #fp.close()
    elif filename.endswith ('.csv'):
        data = pd.read_csv(filename)
        length_framework = len(data)
        if session_username != "" and session_password != "" :
            if 'IP_HostName_FQDN' in data.columns:
                for i in range (0,length_framework) :
                    ip = data.IP_HostName_FQDN[i]
                    if ip=="": continue #empty line in .csv file
                    ip_list[ip] = {}
                    ip_list[ip]["username"] = session_username
                    ip_list[ip]["password"] = session_password
            else:
                print("ERROR: Invalid Column name, it should be IP_HostName_FQDN")
        elif session_username != "" and session_password == "":
            if 'IP_HostName_FQDN' in data.columns and 'Password' in data.columns:
                for i in range (0,length_framework) :
                    ip = data.IP_HostName_FQDN[i]
                    if ip=="": continue #Empty IP in .csv file
                    if (pd.isna(data.Password[i])):
                        print("WARNING: Password missing for "+ ip)
                    else:
                        password = data.Password[i]
                        ip_list[ip] = {}
                        ip_list[ip]["username"] = session_username
                        ip_list[ip]["password"] = password
            else:
                print("ERROR: Invalid Column name, it should be IP_HostName_FQDN and Password")
        elif session_password != "" and session_username == "" :
            if 'IP_HostName_FQDN' in data.columns and 'Username' in data.columns:
                for i in range (0,length_framework) :
                    ip = data.IP_HostName_FQDN[i]
                    if ip=="": continue #Empty IP in .csv file
                    if (pd.isna(data.Username[i])):
                        print("WARNING: Username missing for "+ ip)
                    else:
                        username = data.Username[i]
                        ip_list[ip] = {}
                        ip_list[ip]["username"] = username
                        ip_list[ip]["password"] = session_password
            else:
                print("ERROR: Invalid Column name, it should be IP_HostName_FQDN and Username")
        else:
            pass
    else:
        print("ERROR: Only csv file or txt file can be processed")
    return ip_list

#file_Processing function reads .csv file or .txt file and captures IP Addresses/Hostnames, password and username in ip_list dictonary
#IP;User Name;Password is the format of the file,if password and username are in the file they are extracted here
#lines beginning with "#" in .txt file are omitted
#Headers for CSV files are IP,User and Password
def file_Processing(filename):
    ip_list = {}
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
                            print("WARNING: IP_HostName_FQDN is missing in line %s" % line)
                            continue
                        username = ip_split[1]
                        password = ip_split[2]
                        if(username != "" and password != ""):
                            ip_list[ip] = {}
                            ip_list[ip]["username"] = username
                            ip_list[ip]["password"] = password
                        else:
                            ip = ip_split[0]
                            print("WARNING: For " + ip_split[0] + " ';' is added in the input file and either Username or Password or both is not mentioned use --help for more info")
                    else:
                        print("WARNING: For " + ip_split[0] + " ';' is added in the input file and either Username or Password or both is not mentioned use --help for more info")
                else:
                    ip = ip_row
                    print("WARNING: For "+ip+" has missing Username or Password or both in the input file use --help for more info")
        fp.close #fp.close()
    elif filename.endswith ('.csv'):
        data = pd.read_csv(filename)
        length_framework = len(data)
        if 'Username' in data.columns and 'Password' in data.columns and 'IP_HostName_FQDN' in data.columns:
            for i in range (0,length_framework) :
                ip = data.IP_HostName_FQDN[i]
                if ip=="":
                    continue
                if(pd.isna(data.Username[i]) or pd.isna(data.Password[i]) ): #username or password any is empty!!
                        print( "WARNING: "+ip+" has missing Username/PWD or both in .csv file")
                else: #if both are not empty
                        ip_list[ip] = {}
                        ip_list[ip]["username"] = data.Username[i]
                        ip_list[ip]["password"] = data.Password[i]
        else:
            print("ERROR: Invalid column names given.\nIP_HostName_FQDN,Username,Password are column names")

    else:
        print("ERROR: Only csv file or txt file can be processed")
    return ip_list

#target_file_Processing inputs file and generates prompts for user/password for each entry in the file
#default filename is list.txt
def target_file_Processing(filename):
    ipadd = []
    if filename.endswith('.txt'):
        fp = open(filename, 'r')
        lines = fp.readlines()
        for line in lines:
            iscomment = line.startswith('#')
            if not iscomment and line.strip() != "":
                if(";" in line):
                    ip = line.split(';')[0]
                    if ip=="":
                        print("WARNING: IP_HostName_FQDN missing in line %s" % line)
                        continue
                else:
                    ip = line.rstrip('\n')
                ipadd.append(ip)
        fp.close
    elif filename.endswith('.csv'):
        data = pd.read_csv(filename)
        if 'IP_HostName_FQDN' in data.columns:
            for ip in data.IP_HostName_FQDN :
                if ip!="":ipadd.append(ip)
        else:
            print("ERROR: Invalid column name for IP_HostName_FQDN")
    else:
        print("ERROR: Only csv file or txt file can be processed")
    return ipadd

#database_Processing will return the IP entries from pysqlitecipher.db that are needed using filename
#database holds the password of pysqlitecipher.db
def database_Processing(filename):
    database = getpass.getpass(prompt='Enter the Database Password: ')
    ip_list = {}
    done = []
    ipadd = target_file_Processing(filename)
    tableName = "IP_List_Details"
    try:
        obj = sqlitewrapper.SqliteCipher(dataBasePath="pysqlitecipher.db" , checkSameThread=False , password=database)
        try:
            existingTableEntries = obj.getDataFromTable(tableName, raiseConversionError = True, omitID = False)[1] #[colname1,colname2,colname3][[0,"IP1","u1","p1"],[1,"IP2","u2","p2"],[2,"IP3","u3","p3"]]
            if existingTableEntries != []:
                for entry in existingTableEntries:
                    if entry[1] in ipadd:
                        ip_list[entry[1]]={'username':entry[2],'password':entry[3]}
                        done.append(entry[1])
                for ip in ipadd:
                    if ip not in done:
                        print("WARNING: Missing Credentials in database for "+ ip)

            else:
                print("ERROR: No entries in the database, Please add the details by running database_update.py")
        except:
            print("ERROR: No entries in the database, Please add the details by running database_update.py")

    except:
        print("ERROR: Entered the incorrect Database password")
    return ip_list


#target_Processing based on different Modes will generate ip_list which has IP/Hostname ,User and Password details
#The ip_list is generated based on the prompt type chosen
def target_Processing(target, filename="list.txt"):
    ip_list = {}
    if(target == "prompt"):
        print("INFO: Prompts for individual IP_HostName_FQDN")
        ip = input("Enter the IP_HostName_FQDN: ")
        username = input("Enter the Username: ")
        password = getpass.getpass(prompt='Enter the Password: ')
        if(ip != "" and username != "" and password != ""):
            ip_list[ip] = {}
            ip_list[ip]["username"] = username
            ip_list[ip]["password"] = password
        else:
            print("WARNING: Missing Credentials for "+ip)
    elif(target == "promptall"):
        print("INFO: Prompts Username and Password for all IP_HostName_FQDN in input file")
        ipadd = []
        ipadd = target_file_Processing(filename)
        for ip in ipadd:
            print("Enter the details for "+ip)
            username = input("Enter the Username: ")
            password = getpass.getpass(prompt='Enter the Password: ')
            if username != "" and password != "":
                ip_list[ip] = {}
                ip_list[ip]["username"] = username
                ip_list[ip]["password"] = password
            else:
                print("WARNING: Missing Credentials for "+ip)

    elif "," in target:
        i = len(target.split(","))
        if(i>2):
            print("INFO: Spliting IP_HostName_FQDN,Username,Password to extract credentials")
            ip,username,password = target.split(",")
            if ip!="" and username != "" and password != "":
                ip_list[ip] = {}
                ip_list[ip]["username"] = username
                ip_list[ip]["password"] = password
            else:
                print("WARNING: Missing Credentials for "+ip)

        else:
            ip,val = target.split(",")
            if(val != "prompt"):
                print("Do you mean prompt?")
                print("exiting...")
            elif ip=="":
                print("IP_HostName_FQDN is missing")
                print("exiting...")
            else:
                print("INFO: Prompts Username and Password for "+ ip)
                ip_list[ip] = {}
                ip_list[ip]["username"] = input("Enter the Username: ")
                ip_list[ip]["password"] = getpass.getpass(prompt='Enter the Password: ')
    else:
        print("ERROR: Proper Targets were not choosen, use --help to know more")
    return ip_list

#get_FirmwareInventory obtains different reports based on the flags
#Node Discovery Report has IP Address,host Name,Server Model obtained when discovery=true
#Node Inventory Report has IP Address,host Name,Server Model,BMC Version,BIOS Version obtained when inventory=true
#All Firmware Inventory Report has all the Firmware details obtained when all=true
def get_FirmwareInventory(ip, target_list, login_username, login_password, all, discovery, inventory ):
    try:
        REST_OBJ = redfish.redfish_client(base_url='https://'+ip, username=login_username, password=login_password, default_prefix='/redfish/v1')
        REST_OBJ.login(auth="session")
    except Exception:
        print("WARNING: Error opening session to %s" % ip)
        #print(sys.exc_info())
        return
    test =  re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    index = len(target_list)+1
    result = test.match(ip)
    target_list[index] = {}
    if not result:
        #target_list[index]['HostName'] = ip or #target_list[index]['FQDN']=ip
        #assume both are same for now
        target_list[index]['HostName'] = ip
        target_list[index]['FQDN']=ip
        target_list[index]['IP Address'] = ""
    else:
        target_list[index]['IP Address'] = ip
        target_list[index]['HostName'] = ""
        target_list[index]['FQDN']=""
    models = []
    arr = {}
    sys_count = 0

    try:
        response = REST_OBJ.get('/redfish/v1/UpdateService/FirmwareInventory')
        data = response.dict
        for oid1 in data[u'Members']:
            api1 = oid1.get('@odata.id')
            try:
                req1 = REST_OBJ.get(api1)
                data1 = req1.dict
                value1 = data1[u'Name']
                value2 = data1[u'Version']
                if not discovery:
                    if all:
                        if value1 == "BMCImage1":
                           arr["BMC Ver"] = value2 
                        elif value1 == "BMCImage2":
                           arr["BMC Recovery Ver"] = value2 
                        else:
                            arr[value1 + " Ver"] = value2
                    elif 'BIOS' in value1.upper() or 'BMC' in value1.upper() or search("BIOS", value1.upper()):
                        if not search("VBIOS", value1.upper()) and not search("BMCImage2",value1) and not search("BIOS2", value1):
                            if value1 == "BMCImage1":
                               arr["BMC Ver"] = value2
                            else:
                                arr[value1 + " Ver"] = value2
                        if inventory:
                            target_list[index].update(arr)
            except:
                pass

            target_list[index].update(arr)

    except:
        print("WARNING: Error in getting FirmwareInventory details for "+ip)

    try:
        try:
            response1 = REST_OBJ.get('/redfish/v1/Managers') 
            data2 = response1.dict
            model_info = 'Server Model'
            found=False
            for oid2 in data2[u'Members']: #Managers/Self
                api2 = oid2.get('@odata.id')
                req2 = REST_OBJ.get(api2)
                data3 = req2.dict
                for oid3 in data3[u'EthernetInterfaces']: #Managers/Self/EthernetInterfaces
                    api3 = data3[u'EthernetInterfaces'][oid3]
                    req3 = REST_OBJ.get(api3)
                    data4 = req3.dict
                    for oid4 in data4[u'Members']: #Managers/Self/EthernetInterfaces/eth0
                        api4 = oid4.get('@odata.id')
                        req4= REST_OBJ.get(api4)
                        data5 = req4.dict
                        if "IPv4Addresses" in data5 and "HostName" in data5 and "FQDN" in data5:
                            #Given input is HostName or FQDN
                            if target_list[index]['IP Address'] == "" and (data5["HostName"]!=target_list[index]['HostName'] and data5["FQDN"]!=target_list[index]['FQDN']):
                                found=False
                            #If input given is HostName or FQDN
                            elif target_list[index]['IP Address'] == "":
                                if data5["HostName"]==target_list[index]['HostName']:
                                    target_list[index]['IP Address'] = data5["IPv4Addresses"][0]["Address"]
                                    if target_list[index]['IP Address']  not in IP_HostName_FQDN.keys():
                                        #print("line 420: ",target_list[index]['IP Address'])
                                        #print("target_list ", target_list)
                                        IP_HostName_FQDN[target_list[index]['IP Address']]={}
                                        IP_HostName_FQDN[target_list[index]['IP Address']]['HostName'] = data5["HostName"]     
                                        IP_HostName_FQDN[target_list[index]['IP Address']]['FQDN']=data5['FQDN'] 
                                    target_list[index]['FQDN']=data5['FQDN']          
                                    found=True
                                elif data5["FQDN"]==target_list[index]['FQDN']:
                                    target_list[index]['IP Address'] = data5["IPv4Addresses"][0]["Address"]
                                    if target_list[index]['IP Address']  not in IP_HostName_FQDN.keys():
                                        IP_HostName_FQDN[target_list[index]['IP Address']]={}
                                        IP_HostName_FQDN[target_list[index]['IP Address']]["HostName"] = data5['HostName']   
                                        IP_HostName_FQDN[target_list[index]['IP Address']]["FQDN"]=data5["FQDN"]
                                    target_list[index]['HostName']=data5['HostName']         
                                    found=True
                            #If input given is IP
                            elif  target_list[index]['IP Address'] != "":
                                if data5["IPv4Addresses"][0]["Address"]==target_list[index]['IP Address']:
                                    target_list[index]['HostName'] = data5["HostName"]
                                    target_list[index]['FQDN']=data5["FQDN"]
                                    if target_list[index]['IP Address']  not in IP_HostName_FQDN.keys():
                                        IP_HostName_FQDN[target_list[index]['IP Address']]={}
                                        IP_HostName_FQDN[target_list[index]['IP Address']]["HostName"] = data5["HostName"]
                                        IP_HostName_FQDN[target_list[index]['IP Address']]["FQDN"] = data5["FQDN"]
                                    found=True
                        if found:break
                    if found:break
                if found:break
            if not found:
                print("ERROR: Invalid HostName/FQDN",target_list[index]['HostName'],"is passed. It should be a valid hostname or FQDN as reported by the DNS")
                # print("ERROR: Invalid HostName/FQDN",target_list[index]['FQDN'], " is passed. It should be a valid hostname or FQDN as reported by the DNS")
                del target_list[index]
                return 
        except:
            traceback.print_exc()
            print("WARNING: Error in getting Managers details for "+ip)
        response2 = REST_OBJ.get('/redfish/v1/Systems')
        data6 = response2.dict
        model_info = 'Server Model'
        for oid5 in data6[u'Members']:
            api5 = oid5.get('@odata.id')
            req5 = REST_OBJ.get(api5)
            data7 = req5.dict
            if 'Model' in data7:
                model = data7[u'Model']
                if model is not None:
                    model = model[:15]
                else:
                    model = 'None'
            else:
                model = 'None'
            if 'BiosVersion' in data7 and (inventory or all):
                target_list[index]["BIOS Ver"] = data7[u'BiosVersion'] 

            models.insert(sys_count, model)
            arr[model_info] = models[sys_count]
            sys_count += 1
        target_list[index]["Model"] = model
    except:
        traceback.print_exc()
        print("WARNING: Error in getting Systems details for "+ip)
    REST_OBJ.logout()

#finds HostName for corresponding IP addresss from target_list and vice versa
def find_in_target_list(find_HostName, find_IP, find_FQDN, ip, target_list):
    if find_HostName and find_IP and find_FQDN:
        for v in target_list.values():
            if (v["HostName"]==ip or v["FQDN"]==ip):
                return v["HostName"], v["IP Address"], v["FQDN"]
    if find_HostName and find_FQDN:
        for v in target_list.values():
            if v["IP Address"]==ip:
                return v["HostName"], v["FQDN"]
    

#Gets Status Details after Firmware Update
def UpdateDetails(ip, update_list, login_username, login_password, Pre_Ver, Model,Update_Nature,target,bmc_success_status,bios_success_status,chassis_reset_status,system_reset_status):
    if Model == "HPE Cray XD670" :
        if target == "BMC" :
            target = "BMCImage1"
      #  elif target == "BIOS":
       #     target = "BIOS"

    arr={}
    try:
        REST_OBJ = redfish.redfish_client(base_url='https://'+ip, username=login_username, password=login_password, default_prefix='/redfish/v1')
        REST_OBJ.login(auth="session")
    except Exception:
        print("ERROR: Error opening session to %s" % ip, end='     ')
        print("WARNING: Unable to access "+ ip)
        print("WARNING: "+target+" update may have likely failed and has hanged the system, wait for sometime and try resetting the Setup")
        #print(sys.exc_info())
        return
    test =  re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    index = len(update_list)+1
    result = test.match(ip)
    update_list[index] = {}
    if not result:
        find_HostName = True
        find_IP=True
        find_FQDN=True        
        update_list[index]['HostName'],update_list[index]['IP Address'],update_list[index]['FQDN'] = find_in_target_list(find_HostName, find_IP, find_FQDN, ip, target_list)

    else:
        update_list[index]['IP Address'] = ip
        find_HostName = True
        find_IP=False
        find_FQDN=True
        update_list[index]['HostName'], update_list[index]['FQDN'] = find_in_target_list(find_HostName, find_IP, find_FQDN, ip, target_list)
   
    try:
        if target == "BIOS":
            response = REST_OBJ.get('/redfish/v1/Systems')
            data = response.dict           
            for oid5 in data[u'Members']:
                api = oid5.get('@odata.id')
                req = REST_OBJ.get(api)
                data1 = req.dict
                if 'BiosVersion' in data1:
                    Post_Ver = data1[u'BiosVersion'] 
        else:
            response = REST_OBJ.get('/redfish/v1/UpdateService/FirmwareInventory/'+target)
            data = response.dict
            Post_Ver = data[u'Version']
        if Post_Ver != Pre_Ver and Update_Nature == "Not Same":
            Status = "Success"
        elif Update_Nature == "Same" and Post_Ver == Pre_Ver:
            if "BMC" in target:
                if ip in bmc_success_status or find_in_target_list(find_HostName, find_IP, find_FQDN, ip, target_list) in bmc_success_status:
                    Status = "Success"
                else:
                    Status = "Fail"
            if "BIOS" in target:
                if (ip in bios_success_status and ip in chassis_reset_status and ip in system_reset_status) or (find_in_target_list(find_HostName, find_IP, find_FQDN, ip, target_list) in bios_success_status and find_in_target_list(find_HostName, find_IP, find_FQDN, ip, target_list) in chassis_reset_status  and find_in_target_list(find_HostName, find_IP, find_FQDN, ip, target_list) in system_reset_status):
                    Status = "Success"
                else:
                    Status = "Fail"
        else:
            Status = "Fail"
        arr["Status"] = Status
        arr["Pre-Ver"] = Pre_Ver
        arr["Post-Ver"] = Post_Ver
        arr["Model"] = Model
        update_list[index].update(arr)
    except:
        print("WARNING: Error in getting FirmwareInventory details for "+ip)
    REST_OBJ.logout()

#check if FirmwareToDeploy.txt/.HPM/input txt
def checkFile(filename):
    file_exists = os.path.exists(filename)
    if not file_exists:
        print("ERROR: "+filename+" does not exist")
        return False
    else:
        return True

#find duplicates from input file .txt/.csv (default is list.txt) when firmware updation is chosen
def target_duplicates(filename, lines, delimiter):
    IP_HostName_FQDNs = []
    for line in lines:
        if not line.startswith('#'):
            IP_HostName_FQDN = line.split(delimiter)[0]
            try:
                if  IP_HostName_FQDN not in IP_HostName_FQDNs:
                    IP_HostName_FQDNs.append(IP_HostName_FQDN)
                else:
                    print("WARNING:",filename,"has Duplicate entries for",IP_HostName_FQDN)
                    print("INFO: Only one entry for a cluster is sufficent for the firmware updation")
                    
            except:
                pass


#find duplicates of FirmwareToDeploy.txt having different firmware version details for same model
def FTD_duplicates(firmwareType, firmware_lines, model_count, firmware_details):
    firmware_info =  {}
    duplicates = []
    for line in firmware_lines:
        iscomment = line.startswith('#')
        if not iscomment and line.strip() != "":
            model_name, firmware_type, firmware_version, file_name_org = line.split(';')
            if firmware_type.upper() == firmwareType:
                if model_name in model_count:
                    model_count[model_name] += 1
                else:
                    model_count[model_name] = 1
                    firmware_info[model_name] = [firmware_version, file_name_org]
    for k,v in model_count.items():
        if int(v) == 1:
            firmware_details[k] = [firmware_info[k][0], firmware_info[k][1]]
        else:
            duplicates.append(k)
    if len(duplicates)>0:
        print("**** ERROR: Exiting...As there is more than one entry for ",end="")
        print(*duplicates,sep=", ",end="") 
        print(" in FirmwareToDeploy.txt ****")
        print("INFO: Please make sure that there is only one entry for ",end="")
        print(*duplicates,sep=", ",end="")
        print(" of",firmwareType,"firmware in FirmwareToDeploy.txt ")
        sys.exit()

    return firmware_details


#update_BMC is wrapper funtion that parses FirmwareDeploy.txt and ip/hostname along with its credentials
#and calls final_bmc to do update, this function also returns Update Status report
def update_BMC(update_list, target_list, ip_list, filename,choice_Force,choice_Debug):
    global not_Done
    bmc_success_status = []
    flag=False
    target_list_copy = {}
    models_present={"Cray XD295v_XD220v_XD225v":0,"Cray XD670":0}
    for key in target_list:
        ip_addr = target_list[key]['IP Address']
        if ip_addr in target_list_copy:
            print("INFO: IP Address:",ip_addr,", HostName:",target_list[key]["HostName"],"and FQDN:",target_list[key]["FQDN"],"must be of a single cluster only")
            continue
        else:
            target_list_copy[ip_addr] = {"BMC Ver": target_list[key]['BMC Ver'], "Server Model": target_list[key]['Model']} 
            if (target_list[key]['Model']=="HPE Cray XD220v" or target_list[key]['Model']=="HPE Cray XD225v" or target_list[key]['Model']=="HPE Cray XD295v"):
                if "Cray XD295v_XD220v_XD225v" not in models_present:
                    models_present["Cray XD295v_XD220v_XD225v"]=1
                else:
                    models_present["Cray XD295v_XD220v_XD225v"]+=1
            elif target_list[key]['Model']=="HPE Cray XD670":
                if "Cray XD670" not in models_present:
                    models_present["Cray XD670"]=1
                else:
                    models_present["Cray XD670"]+=1
    print("****INFO: BMC Update Proceeding for: ",end="")
    items = ', '.join(f'{value} {key} models' for key, value in models_present.items())
    print(items)
    ip_list_cpy = ip_list.copy()
    fp = open(filename, 'r')
    lines = fp.readlines()
    threads = []
    model_count = {}
    firmware_details = {}
    firmware_details = FTD_duplicates("BMC", lines, model_count, firmware_details)
    for model_name,firmware_detail in firmware_details.items():
        bmc_file = firmware_detail[1].splitlines()[0]
        for ip in list(target_list_copy):
            try:
                existing_Version = target_list_copy[ip]["BMC Ver"]        
                model_ip = target_list_copy[ip]["Server Model"]
                if(model_name == model_ip):
                    if checkFile(bmc_file):
                        if(existing_Version != firmware_detail[0] or choice_Force ):
                            flag=True
                            #ip is IP Address
                            #ip_list can have anything as keys 
                            try:
                                ip_list[ip]["Pre-Ver"] = existing_Version
                                ip_list[ip]["Model"] = model_ip
                            except:
                                try:
                                    ip_list[IP_HostName_FQDN[ip]["HostName"]]["Pre-Ver"] = existing_Version
                                    ip_list[IP_HostName_FQDN[ip]["HostName"]]["Model"] = model_ip
                                except:
                                    ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Pre-Ver"] = existing_Version
                                    ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Model"] = model_ip
                            if existing_Version == firmware_detail[0]:
                                try:
                                    ip_list[ip]["Update_Nature"] = "Same"   
                                except:
                                    try:
                                        ip_list[IP_HostName_FQDN[ip]["HostName"]]["Update_Nature"] = "Same"
                                    except:
                                        ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Update_Nature"] = "Same"
                            else:
                                try:
                                    ip_list[ip]["Update_Nature"] = "Not Same"
                                except:
                                    try:
                                        ip_list[IP_HostName_FQDN[ip]["HostName"]]["Update_Nature"] = "Not Same"
                                    except:
                                        ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Update_Nature"] = "Not Same"
                            try:
                                thread = threading.Thread(target = call_bmc_function, args = (ip, ip_list_cpy[ip]["username"], ip_list_cpy[ip]["password"], bmc_file ,bmc_success_status,ip_list[ip]["Model"],choice_Debug))
                            except:
                                try:
                                    thread = threading.Thread(target = call_bmc_function, args = (IP_HostName_FQDN[ip]["HostName"], ip_list_cpy[IP_HostName_FQDN[ip]["HostName"]]["username"], ip_list_cpy[IP_HostName_FQDN[ip]["HostName"]]["password"], bmc_file ,bmc_success_status,ip_list[IP_HostName_FQDN[ip]["HostName"]]["Model"], choice_Debug))
                                except:
                                    thread = threading.Thread(target = call_bmc_function, args = (IP_HostName_FQDN[ip]["FQDN"], ip_list_cpy[IP_HostName_FQDN[ip]["FQDN"]]["username"], ip_list_cpy[IP_HostName_FQDN[ip]["FQDN"]]["password"], bmc_file ,bmc_success_status,ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Model"], choice_Debug))
                            thread.start()
                            threads.append(thread)
                            try:
                                #deleting ip from ip_list_cpy to avoid reiteration
                                del ip_list_cpy[ip]
                            except:
                                try:
                                    del ip_list_cpy[IP_HostName_FQDN[ip]["HostName"]]
                                except:
                                    del ip_list_cpy[IP_HostName_FQDN[ip]["FQDN"]]
                        else:
                            print("WARNING: Update is halted because Force argument is not set, as the version is same as suggested for the cluster having IP:",ip,", Hostname:",IP_HostName_FQDN[ip]["HostName"],"and FQDN: ",IP_HostName_FQDN[ip]["FQDN"] )
                            not_Done+=1
                            if target_list_copy[ip]["Server Model"] == "HPE Cray XD220v" or target_list_copy[ip]['Server Model']=="HPE Cray XD225v" or target_list_copy[ip]['Server Model']=="HPE Cray XD295v":
                                models_present["Cray XD295v_XD220v_XD225v"]-=1
                            elif target_list_copy[ip]['Server Model']=="HPE Cray XD670":
                                models_present["Cray XD670"]-=1
                            print("****INFO: BMC Update Proceeding for: ",end="")
                            items = ', '.join(f'{value} {key} models' for key, value in models_present.items())
                            print(items)
                            continue
                    else:
                        print("WARNING: Error in the filename for "+ model_name+" update skipped for the cluster having IP:",ip,", Hostname:"+IP_HostName_FQDN[ip]["HostName"],"and FQDN:",IP_HostName_FQDN[ip]["FQDN"])
                        not_Done+=1
                        if target_list_copy[ip]["Server Model"] == "HPE Cray XD220v" or target_list_copy[ip]['Server Model']=="HPE Cray XD225v" or target_list_copy[ip]['Server Model']=="HPE Cray XD295v":
                            models_present["Cray XD295v_XD220v_XD225v"]-=1
                        elif target_list_copy[ip]['Server Model']=="HPE Cray XD670":
                            models_present["Cray XD670"]-=1
                        print("****INFO: BMC Update Proceeding for: ",end="")
                        items = ', '.join(f'{value} {key} models' for key, value in models_present.items())
                        print(items)
                        continue
            except:
                print("** Cluster having IP:",ip,", Hostname:",IP_HostName_FQDN[ip]["HostName"],"and FQDN:",IP_HostName_FQDN[ip]["FQDN"],"is not reachable!!!")
                not_Done+=1
                if target_list_copy[ip]["Server Model"] == "HPE Cray XD220v" or target_list_copy[ip]['Server Model']=="HPE Cray XD225v" or target_list_copy[ip]['Server Model']=="HPE Cray XD295v":
                    models_present["Cray XD295v_XD220v_XD225v"]-=1
                elif target_list_copy[ip]['Server Model']=="HPE Cray XD670":
                    models_present["Cray XD670"]-=1
                print("****INFO: BMC Update Proceeding for: ",end="")
                items = ', '.join(f'{value} {key} models' for key, value in models_present.items())
                print(items)
                flag=False
                continue


    for thread in threads:
        thread.join()
    if not len(target_list)==not_Done:
        print("**** INFO: Total",len(target_list)-not_Done,"done ****")
        print("INFO: Please wait for reports to know the status of firmware update.")
    fp.close
    if flag:
        print("INFO: Sleeping for 5 minutes to let BMC reset to happen in the background")
        time.sleep(300)
    threads = []
    for ipadd in ip_list.keys():
        key = "Pre-Ver"
        if key in ip_list[ipadd].keys():
            try:
                thread = threading.Thread(target = UpdateDetails, args = (ipadd, update_list, ip_list[ipadd]["username"], ip_list[ipadd]["password"], ip_list[ipadd]["Pre-Ver"], ip_list[ipadd]["Model"],ip_list[ipadd]["Update_Nature"],"BMC",bmc_success_status,[],[],[]))
            except:
                try:
                    thread = threading.Thread(target = UpdateDetails, args = (ipadd, update_list, ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["username"], ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["password"], ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["Pre-Ver"], ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["Model"],ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["Update_Nature"],"BMC",bmc_success_status,[],[],[]))
                except:
                    thread = threading.Thread(target = UpdateDetails, args = (ipadd, update_list, ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["username"], ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["password"], ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["Pre-Ver"], ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["Model"],ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["Update_Nature"],"BMC",bmc_success_status,[],[],[]))
    
            thread.start()
            threads.append(thread)
    for thread in threads:
        thread.join()

#update_BIOS is wrapper funtion that parses FirmwareDeploy.txt and ip/hostname along with its credentials
#and calls final_bios function to do update
def update_BIOS(update_list, target_list, ip_list, filename,choice_powercycle,choice_Force,choice_Debug):
    global not_Done
    flag=False
    reset_list = {}
    threads = []
    chassis_reset_status = []
    system_reset_status = []
    bios_success_status = []
    target_list_copy = {}
    models_present={"Cray XD295v_XD220v_XD225v":0,"Cray XD670":0}
    for key in target_list:
        ip_addr = target_list[key]['IP Address']
        if ip_addr in target_list_copy:
            print("INFO:",ip_addr,"and",target_list[key]["HostName"],"must be of a single cluster only")
            continue
        else:
            target_list_copy[ip_addr] = {"BIOS Ver": target_list[key]['BIOS Ver'], "Server Model": target_list[key]['Model']}
            if (target_list[key]['Model']=="HPE Cray XD220v" or target_list[key]['Model']=="HPE Cray XD225v" or target_list[key]['Model']=="HPE Cray XD295v"):
                if "Cray XD295v_XD220v_XD225v" not in models_present:
                    models_present["Cray XD295v_XD220v_XD225v"]=1
                else:
                    models_present["Cray XD295v_XD220v_XD225v"]+=1
            elif target_list[key]['Model']=="HPE Cray XD670":
                if "Cray XD670" not in models_present:
                    models_present["Cray XD670"]=1
                else:
                    models_present["Cray XD670"]+=1
    print("****INFO: BIOS Update Proceeding for: ",end="")
    items = ', '.join(f'{value} {key} models' for key, value in models_present.items())
    print(items)
    ip_list_cpy = ip_list.copy()
    fp = open(filename, 'r')
    lines = fp.readlines()
    model_count = {}
    firmware_details = {}
    firmware_details = FTD_duplicates("BIOS", lines, model_count, firmware_details)
    
    for model_name,firmware_detail in firmware_details.items():
        bios_file = firmware_detail[1].splitlines()[0]
        for ip in list(target_list_copy):
            try:
                existing_Version = target_list_copy[ip]["BIOS Ver"]
                model_ip = target_list_copy[ip]["Server Model"]
                if(model_name == model_ip):
                    if checkFile(bios_file):
                        if(existing_Version != firmware_detail[0] or choice_Force):
                            flag=True
                            #print("INFO: Update Proceeding for: "+ip)
                            try:
                                ip_list[ip]["Pre-Ver"] = existing_Version
                                ip_list[ip]["Model"] = model_ip
                            except:
                                try:
                                    ip_list[IP_HostName_FQDN[ip]["HostName"]]["Pre-Ver"]=existing_Version
                                    ip_list[IP_HostName_FQDN[ip]["HostName"]]["Model"]=model_ip
                                except:
                                    ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Pre-Ver"]=existing_Version
                                    ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Model"]=model_ip
                                
                            if existing_Version == firmware_detail[0]:
                                try:
                                    ip_list[ip]["Update_Nature"] = "Same"
                                except:
                                    try:
                                        ip_list[IP_HostName_FQDN[ip]["HostName"]]["Update_Nature"] = "Same"
                                    except:
                                        ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Update_Nature"] = "Same"
                            else:
                                try:
                                    ip_list[ip]["Update_Nature"] = "Not Same"
                                except:
                                    try:
                                        ip_list[IP_HostName_FQDN[ip]["HostName"]]["Update_Nature"] = "Not Same"
                                    except:
                                        ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Update_Nature"] = "Not Same"
                            try:
                                thread = threading.Thread(target = call_bios_function, args = (ip, ip_list_cpy[ip]["username"], ip_list_cpy[ip]["password"], bios_file , bios_success_status,ip_list[ip]["Model"],choice_Debug))
                            except:
                                try:
                                    thread = threading.Thread(target = call_bios_function, args = (IP_HostName_FQDN[ip]["HostName"], ip_list_cpy[IP_HostName_FQDN[ip]["HostName"]]["username"], ip_list_cpy[IP_HostName_FQDN[ip]["HostName"]]["password"], bios_file , bios_success_status,ip_list[IP_HostName_FQDN[ip]["HostName"]]["Model"],choice_Debug))
                                except:
                                    thread = threading.Thread(target = call_bios_function, args = (IP_HostName_FQDN[ip]["FQDN"], ip_list_cpy[IP_HostName_FQDN[ip]["FQDN"]]["username"], ip_list_cpy[IP_HostName_FQDN[ip]["FQDN"]]["password"], bios_file , bios_success_status,ip_list[IP_HostName_FQDN[ip]["FQDN"]]["Model"],choice_Debug))                                   
                            thread.start()
                            threads.append(thread)
                            try:
                                del ip_list_cpy[ip]
                            except:
                                try:
                                    del ip_list_cpy[IP_HostName_FQDN[ip]["HostName"]]
                                except:
                                    del ip_list_cpy[IP_HostName_FQDN[ip]["FQDN"]]

                        else:
                            not_Done+=1
                            if target_list_copy[ip]["Server Model"] == "HPE Cray XD220v" or target_list_copy[ip]['Server Model']=="HPE Cray XD225v" or target_list_copy[ip]['Server Model']=="HPE Cray XD295v":
                                models_present["Cray XD295v_XD220v_XD225v"]-=1
                            elif target_list_copy[ip]['Server Model']=="HPE Cray XD670":
                                models_present["Cray XD670"]-=1
                            print("WARNING: Update is halted because Force argument is not set, as the version is same as suggested for the cluster having IP:",ip,", Hostname:",IP_HostName_FQDN[ip]["HostName"],"and FQDN:",IP_HostName_FQDN[ip]["FQDN"] )
                            print("****INFO: BIOS Update Proceeding for: ",end="")
                            items = ', '.join(f'{value} {key} models' for key, value in models_present.items())
                            print(items)
                            continue
                    else:
                        print("WARNING: Error in the filename for",model_name,"update skipped for the cluster having IP:",ip,", Hostname:",IP_HostName_FQDN[ip]["HostName"],"and FQDN:",IP_HostName_FQDN[ip]["FQDN"])
                        not_Done+=1
                        if target_list_copy[ip]["Server Model"] == "HPE Cray XD220v" or target_list_copy[ip]['Server Model']=="HPE Cray XD225v" or target_list_copy[ip]['Server Model']=="HPE Cray XD295v":
                            models_present["Cray XD295v_XD220v_XD225v"]-=1
                        elif target_list_copy[ip]['Server Model']=="HPE Cray XD670":
                            models_present["Cray XD670"]-=1
                        print("****INFO: BIOS Update Proceeding for: ",end="")
                        items = ', '.join(f'{value} {key} models' for key, value in models_present.items())
                        print(items)
                        continue
            except:
                print("**ERROR: Cluster having IP:"+ip,", Hostname:",IP_HostName_FQDN[ip]["HostName"],"and FQDN:",IP_HostName_FQDN[ip]["FQDN"],"is not reachable!!!")
                flag =False
                not_Done+=1
                if target_list_copy[ip]["Server Model"] == "HPE Cray XD220v" or target_list_copy[ip]['Server Model']=="HPE Cray XD225v" or target_list_copy[ip]['Server Model']=="HPE Cray XD295v":
                    models_present["Cray XD295v_XD220v_XD225v"]-=1
                elif target_list_copy[ip]['Server Model']=="HPE Cray XD670":
                    models_present["Cray XD670"]-=1
                print("****INFO: BIOS Update Proceeding for: ",end="")
                items = ', '.join(f'{value} {key} models' for key, value in models_present.items())
                print(items)
                continue


    for thread in threads:
        thread.join()
    if not len(target_list)==not_Done:
        print("**** INFO: Total",len(target_list)-not_Done,"done ****")
        print("INFO: Please wait for reports to know the status of firmware update.")
    fp.close
    if flag:
        if choice_powercycle:
            for k,val in ip_list.items():
                if len(val)>2 and k in bios_success_status: #only do chassis reset/system reset if bios is flashed successfully
                    reset_list[k]=val
            print("INFO: Sleeping for 5 minutes, working on BIOS Update in the Background")
            time.sleep(300)
            Power_Cycling(reset_list,chassis_reset_status,system_reset_status,choice_Debug)
            print("INFO: Sleeping for 5 minutes. Allowing Power_Cycle.py to complete and Update to Reflect")
            time.sleep(300)
            threads = []
            for ipadd in ip_list.keys():
                key = "Pre-Ver"
                if key in ip_list[ipadd].keys():
                    try:
                        thread = threading.Thread(target = UpdateDetails, args=(ipadd, update_list, ip_list[ipadd]["username"], ip_list[ipadd]["password"], ip_list[ipadd]["Pre-Ver"],ip_list[ipadd]["Model"],ip_list[ipadd]["Update_Nature"],"BIOS",[],bios_success_status,chassis_reset_status,system_reset_status))
                    except:
                        try:
                            thread = threading.Thread(target = UpdateDetails, args=(ipadd, update_list, ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["username"], ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["password"], ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["Pre-Ver"],ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["Model"],ip_list[IP_HostName_FQDN[ipadd]["HostName"]]["Update_Nature"],"BIOS",[],bios_success_status,chassis_reset_status,system_reset_status))
                        except:
                            thread = threading.Thread(target = UpdateDetails, args=(ipadd, update_list, ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["username"], ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["password"], ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["Pre-Ver"],ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["Model"],ip_list[IP_HostName_FQDN[ipadd]["FQDN"]]["Update_Nature"],"BIOS",[],bios_success_status,chassis_reset_status,system_reset_status))
                    thread.start()
                    threads.append(thread)
            for thread in threads:
                thread.join()
        else:
            print("INFO: The version changes for BIOS will not be reflected unless we complete an Chassis reset and System reset")
            print("INFO: Please use the -P or --Power for the BIOS version change. It may take around few minutes for version to reflect ")
            print("INFO: Perform Inventory report to know the status")
            print("INFO: Exiting...")
            sys.exit()

description_Details_v1 = """
This program is designed to:

1.Discover which server nodes are part of the HPC population and
  provide a report of the node: model, hostname, FQDN, and IP address
2.Create an Inventory report of HPC population to include a list
  of model type, hostname, FQDN, IP address, and firmware versions of
  all components which the tool can manage
3.Update BMC and BIOS

To generate Discovery and Inventory reports, list.txt which is a
default file can be used, any other file can also be used with -f
option.
Only text file and csv file are processed to generate reports.
Column name of CSV files should be IP,User and Password.
For Text file "#" can be used for comment and IP_HostName_FQDN, Username
and Password are to be seperated by ";"
If all the nodes have same Username and Password -u and -p can be used
for session user details and session password

BMC and BIOS firmware details for different Models are to be mentioned
in "FirmwareToDeploy.txt" file.This file includes a Model name
firmware type, firmware version and filename.
All the parameters are seperated by ";"
This information is used to compare the current version of the firmware with
the baseline version to determine whether it needs to be updated.
The '-z' option will run the UPDATE FIRMWARE commands and generate reports.
The '-P' option will have to be set do AC Powercycle to ensure the firmware update
versions are reflected
The '-F' option will have to be set for force install
"""
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=description_Details_v1,formatter_class=argparse.RawTextHelpFormatter)
    parser.version = '1.1'
    parser.add_argument('-p', '--password', action='store', help="session password, this can be used when all nodes have common password")
    parser.add_argument('-u', '--username', action='store', help="session username, this can be used when all nodes have common username")
    parser.add_argument('-t', '--target', action='store', help='''Target IP_HostName_FQDN for report or Update.
Multiple Modes:
    -t IP_HostName_FQDN,Username,Password - to specify one target.
    -t prompt - prompts for IP_HostName_FQDN,Username,Password of one target
    -t promptall - prompts for Username,Password for all clusters from the file, default is list.txt.
    -t IP_HostName_FQDN,prompt - prompts for Username,Password of one target.
                        ''')
    parser.add_argument('-f', '--filename', action='store', help='''file consisting of IP_HostName_FQDN (Necessary),Username (Optional) and Password
(Optional) seperated by ';' for reports, default is list.txt. If this file has only IP_HostName_FQDN, they can be listed in different lines
            ''' )
    parser.add_argument('-db','--database', action='store_true', help='''To be set if the credentials of IP_HostName_FQDN present in the input file are to be extracted from database''')
    parser.add_argument('-c', '--component', action='store', help='''Component for Update.
Multiple Modes:
    -c BMC - to choose BMC Update.
    -c BIOS - to choose BIOS Update
                           ''')
    parser.add_argument('-P', '--Power', action='store_true', help="Applies AC Power Cycles when required for update, if not applied the updates will not be reflected")
    parser.add_argument('-F', '--Force', action='store_true', help="Forces install when the firmware version to be updated is same the existing firmware version.")
    parser.add_argument('-a', '--all', action='store_true', help="It shows all Firmware details")
    parser.add_argument('-d', '--discovery', action='store_true', help="Node Discovery Report displays IP_HostName_FQDN, HostName and ServerModel of HPC cluster")
    parser.add_argument('-i', '--inventory', action='store_true', help="Node Inventory Report displays IP_HostName_FQDN, HostName, ServerModel, BIOS Ver and BMC Ver of HPC cluster")
    parser.add_argument('-z', '--update', action='store_true', help="Firmware Update")
    parser.add_argument('-v', action='version')
    parser.add_argument('-D','--Debug',action='store_true', help="It shows all the debug information while updating the firmware. There is no effect on the report generation.")

    args = parser.parse_args()
    update_list={}
    target_list = dict() # {1: {'IP':ip1, 'BIOS Ver': '00.86.0000', 'BMC Ver': '1.01.0', 'HostName': 'None', 'Server Model': 'HPE Cray XD220v'}, 2: {'IP':ip2,'BIOS Ver': '00.72.0000', 'BMC Ver': '1.00.0', 'HostName': 'None', 'Server Model': 'HPE Cray XD295v'}}
    threads = []
    ip_list = {} #{'IP1':{'user': u1, 'password': p1}, 'IP2':{'user': u2, 'password': p2}}
    filename ='list.txt' #default input is list.txt 

    if args.discovery or args.inventory or args.update or args.all:
            #File selection
        if(args.filename):
            filename = args.filename
        if not args.target and args.update:
            fp = open(filename, 'r')
            lines = fp.readlines()
            if filename.endswith(".txt"):
                delimiter= ";"
            else:
                delimiter=","
            target_duplicates(filename, lines, delimiter)

        #IP Selection
        if(args.username is not None and args.password is not None):
            ip_list = session_Processing(filename,args.username,args.password)
        elif (args.username is None and args.password is not None):
            print("INFO: Only session password was passed, Parsing input file for username")
            ip_list = session_Processing(filename,"",args.password)
        elif(args.password is None and args.username is not None):
            print("INFO: Only session username was passed, Parsing input file for password")
            ip_list = session_Processing(filename,args.username,"")
        elif (args.target):
            ip_list = target_Processing(args.target,filename)
        elif (args.database):
            print("INFO: Extracting Credentials from database for IP_HostName_FQDN in input text file")
            ip_list = database_Processing(filename)
        else:
            print("INFO: No session password and session username common to all nodes was passed as arguments, Parsing the file ")
            ip_list = file_Processing(filename)
        #Report or Update
        if(args.all or args.discovery or args.inventory):
            for ipadd in ip_list.keys():
                thread = threading.Thread(target = get_FirmwareInventory, args=(ipadd, target_list, ip_list[ipadd]["username"], ip_list[ipadd]["password"], args.all, args.discovery, args.inventory))
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join()
            if len(target_list)>0:
                if(args.inventory):
                    print("HPE Node Inventory Report")
                    print()
                    report_name = "NodeInventoryReport"
                elif(args.discovery):
                    print("HPE Node Discovery Report")
                    print()
                    report_name = "NodeDiscoveryReport"
                else:
                    print("HPE All Firmware Inventory Report")
                    print()
                    report_name = "NodeAllFirmwareInventoryReport"

                temp=[]
                new_target_list={}
                for key,val in target_list.items():
                    if val not in temp:
                        temp.append(val)
                        new_target_list[key]=val
                time_Display(new_target_list,False)
                arr = list(range(1,len(new_target_list)+1))
                target_list = dict(zip(arr,list(new_target_list.values()))) 
                i = 0
                df = pd.DataFrame.from_dict({i: target_list[i]
                for i in target_list.keys()},
                    orient='index')
                
                df = df.rename_axis("Sl No")
                ###
                df.reset_index(inplace=True)
                df = df.sort_values(by = ['FQDN'])
                df = df.sort_values(by = ['HostName'])
                df = df.sort_values(by=['IP Address'])
                df = df.where(pd.notnull(df), "NA")
                df.style.set_properties(**{'text-align': 'right'})
                df.sort_index(axis=0)
                df['Sl No'] = df['Sl No'].sort_values(ascending=True).tolist()
                df2 = df.to_string(index=False)
                print(df2)
                output_Save(report_name,"report",df)
        elif args.update: #only when --z is given, actual update happens and only Inventory report is generated
            if len(ip_list)>64:
                print("INFO: Only first 64 IP Address/HostNames are being processed!!!")
                ip_list = ip_list[:64]
            for ipadd in ip_list.keys():
                thread = threading.Thread(target=get_FirmwareInventory, args=(ipadd, target_list, ip_list[ipadd]["username"], ip_list[ipadd]["password"], False, False, True))
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join()

            print("HPE Firmware Update")
            print()
            comp = ""
            comp = args.component
            if comp:
                if comp.upper() == "BMC":
                    firmware_Type = "a"
                elif comp.upper() == "BIOS":
                    firmware_Type = "b"
                else:
                    pass
            else:
                print("Choose the type of firmware for Update (A/a or B/b)?" )
                firmware_Type = input("A)BMC B)BIOS \n")
            if(firmware_Type.lower() =="a"  ):
                print("INFO: BMC Update is Selected")
                update_BMC(update_list, target_list, ip_list, "FirmwareToDeploy.txt",args.Force, args.Debug)
                if len(update_list) > 0 :
                    print("HPE Firmware Update Status Report")
                    time_Display(update_list,True)
                    arr = list(range(1,len(update_list)+1))
                    target_list = dict(zip(arr,list(update_list.values()))) 
                    i = 0
                    df = pd.DataFrame.from_dict({i: update_list[i]
                    for i in update_list.keys()},
                        orient='index')
                    df = df.rename_axis("Sl No")
                    df.reset_index(inplace=True)
                    
                    df = df.sort_values(by = ['FQDN'])
                    df = df.sort_values(by = ['HostName'])
                    df = df.sort_values(by=['IP Address'])
                    df.style.set_properties(**{'text-align': 'right'})
                    df.sort_index(axis=0)
                    df['Sl No'] = df['Sl No'].sort_values(ascending=True).tolist()
                    df2 = df.to_string(index=False)
                    print(df2)
                    report_name = "UpdateStatusReport_BMC"
                    output_Save(report_name,"update",df)
                else:
                    print("INFO: No update was done")

            elif (firmware_Type.lower() == "b"):
                print("INFO: BIOS Update Selected")
                if not args.Power:
                    print("INFO: AC Power Cycling is not chosen for BIOS Update")
                else:
                    print("INFO: BIOS Update may take upto 20-25 minutes as it includes AC Power Cycling and Update Status Display")
                update_BIOS(update_list,target_list,ip_list,"FirmwareToDeploy.txt",args.Power,args.Force, args.Debug)
                if len(update_list) > 0 :
                    print("HPE Firmware Update Status Report")
                    time_Display(update_list,True)
                    arr = list(range(1,len(update_list)+1))
                    target_list = dict(zip(arr,list(update_list.values()))) 
                    i = 0
                    df = pd.DataFrame.from_dict({i: update_list[i]
                    for i in update_list.keys()},
                        orient='index')
                    df = df.rename_axis("Sl No")
                    df.reset_index(inplace = True)
                    
                    df = df.sort_values(by = ['FQDN'])
                    df = df.sort_values(by = ['HostName'])
                    df = df.sort_values(by=['IP Address'])
                    df.style.set_properties(**{'text-align': 'right'})
                    df.sort_index(axis=0)
                    df['Sl No'] = df['Sl No'].sort_values(ascending=True).tolist()
                    df2 = df.to_string(index=False)
                    print(df2)
                    report_name = "UpdateStatusReport_BIOS"
                    output_Save(report_name,"update",df)
                else:
                    print("INFO: No update was done")
            else:
                print("ERROR: Enter valid value")
        else:
            pass

    else:
        print("ERROR: Give parameters for report or update, use --help for more information")




