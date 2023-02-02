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
from bmc_update import *
from bios_update import *
from Power_Cycle import *
from pysqlitecipher import sqlitewrapper
import getpass
import re
import traceback

global IP_HostName
IP_HostName = dict()
#if IP is given, HostName is found and it is kept as {IP:HostName} pair
#if HostName is given, IP is found and it is kept as {IP:HostName} pair

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
        print(str(len_nodes) + ' items found, ', success_count, " success, ", fail_count, " failure")
    else:
        print(str(len_nodes) + ' items found')
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
                        print("WARNING: IP Address/HostName missing in the line: ",line)
                        continue
                    if(session_username != "" and session_password != ""):
                        ip_list[ip] = {}
                        ip_list[ip]["user"] = session_username
                        ip_list[ip]["password"] = session_password
                    if(session_username == "" and session_password != ""):
                        if len(ip_split) > 1 :
                            if ip_split[1] != "":
                                username = ip_split[1]
                                ip_list[ip] = {}
                                ip_list[ip]["user"] = username
                                ip_list[ip]["password"] = session_password
                            else:
                                print("WARNING: Username missing for "+ ip)
                    if(session_username != "" and session_password == ""):
                        if len(ip_split) > 2 :
                            if ip_split[2] != "":
                                password = ip_split[2]
                                ip_list[ip] = {}
                                ip_list[ip]["user"] = session_username
                                ip_list[ip]["password"] = password
                            else:
                                print("WARNING: Password missing for "+ ip)
                else:
                    ip = ip_row
                    if(session_username != "" and session_password != ""):
                        ip_list[ip] = {}
                        ip_list[ip]["user"] = session_username
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
            if 'IP' in data.columns:
                for i in range (0,length_framework) :
                    ip = data.IP[i]
                    if ip=="": continue #empty line in .csv file
                    ip_list[ip] = {}
                    ip_list[ip]["user"] = session_username
                    ip_list[ip]["password"] = session_password
            else:
                print("ERROR: Invalid Column name, it should be IP")
        elif session_username != "" and session_password == "":
            if 'IP' in data.columns and 'Password' in data.columns:
                for i in range (0,length_framework) :
                    ip = data.IP[i]
                    if ip=="": continue #Empty IP in .csv file
                    if (pd.isna(data.Password[i])):
                        print("WARNING: Password missing for "+ ip)
                    else:
                        password = data.Password[i]
                        ip_list[ip] = {}
                        ip_list[ip]["user"] = session_username
                        ip_list[ip]["password"] = password
            else:
                print("ERROR: Invalid Column name, it should be IP and Password")
        elif session_password != "" and session_username == "" :
            if 'IP' in data.columns and 'User' in data.columns:
                for i in range (0,length_framework) :
                    ip = data.IP[i]
                    if ip=="": continue #Empty IP in .csv file
                    if (pd.isna(data.User[i])):
                        print("WARNING: Username missing for "+ ip)
                    else:
                        username = data.User[i]
                        ip_list[ip] = {}
                        ip_list[ip]["user"] = username
                        ip_list[ip]["password"] = session_password
            else:
                print("ERROR: Invalid Column name, it should be IP and User")
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
                            print("WARNING: IP Address/HostName missing in line %s" % line)
                            continue
                        username = ip_split[1]
                        password = ip_split[2]
                        if(username != "" and password != ""):
                            ip_list[ip] = {}
                            ip_list[ip]["user"] = username
                            ip_list[ip]["password"] = password
                        else:
                            ip = ip_split[0]
                            print("WARNING: For " + ip_split[0] + " ';' is added in the input file and either Username/PWD or both is not mentioned use --help for more info")
                    else:
                        print("WARNING: For " + ip_split[0] + " ';' is added in the input file and either Username/PWD or both is not mentioned use --help for more info")
                else:
                    ip = ip_row
                    print("WARNING: For "+ip+" has missing Username/PWD or both in the input file use --help for more info")
        fp.close #fp.close()
    elif filename.endswith ('.csv'):
        data = pd.read_csv(filename)
        length_framework = len(data)
        if 'User' in data.columns and 'Password' in data.columns and 'IP' in data.columns:
            for i in range (0,length_framework) :
                ip = data.IP[i]
                if ip=="":
                    continue
                if(pd.isna(data.User[i]) or pd.isna(data.Password[i]) ): #username or password any is empty!!
                        print( "WARNING: "+ip+" has missing Username/PWD or both in .csv file")
                else: #if both are not empty
                        ip_list[ip] = {}
                        ip_list[ip]["user"] = data.User[i]
                        ip_list[ip]["password"] = data.Password[i]
        else:
            print("ERROR: Invalid column names Password,User and IP are column names")

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
                        print("WARNING: IP Address/HostName missing in line %s" % line)
                        continue
                else:
                    ip = line.rstrip('\n')
                ipadd.append(ip)
        fp.close
    elif filename.endswith('.csv'):
        data = pd.read_csv(filename)
        if 'IP' in data.columns:
            for ip in data.IP :
                if ip!="":ipadd.append(ip)
        else:
            print("ERROR: Invalid column name for IP")
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
                        ip_list[entry[1]]={'user':entry[2],'password':entry[3]}
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
        print("INFO: Prompts for individual IP Addresses/HostNames")
        ip = input("Enter the IP Address/Hostname: ")
        username = input("Enter the user name: ")
        password = getpass.getpass(prompt='Enter the Password: ')
        if(ip != "" and username != "" and password != ""):
            ip_list[ip] = {}
            ip_list[ip]["user"] = username
            ip_list[ip]["password"] = password
        else:
            print("WARNING: Missing Credentials for "+ip)
    elif(target == "promptall"):
        print("INFO: Prompts username and password for all IP Addresses/HostNames in input file")
        ipadd = []
        ipadd = target_file_Processing(filename)
        for ip in ipadd:
            print("Enter the details for "+ip)
            username = input("Enter the user name: ")
            password = getpass.getpass(prompt='Enter the Password: ')
            if username != "" and password != "":
                ip_list[ip] = {}
                ip_list[ip]["user"] = username
                ip_list[ip]["password"] = password
            else:
                print("WARNING: Missing Credentials for "+ip)

    elif "," in target:
        i = len(target.split(","))
        if(i>2):
            print("INFO: Spliting IP Address/HostName,Username,Password to extract credentials")
            ip,username,password = target.split(",")
            if ip!="" and username != "" and password != "":
                ip_list[ip] = {}
                ip_list[ip]["user"] = username
                ip_list[ip]["password"] = password
            else:
                print("WARNING: Missing Credentials for "+ip)

        else:
            ip,val = target.split(",")
            if(val != "prompt"):
                print("Do you mean prompt?")
                print("exiting")
            elif ip=="":
                print("IP Address/HostName missing")
                print("exiting")
            else:
                print("INFO: Prompts Username and Password for "+ ip)
                ip_list[ip] = {}
                ip_list[ip]["user"] = input("Enter the user name: ")
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
        target_list[index]['HostName'] = ip
        target_list[index]['IP Address'] = ""
    else:
        target_list[index]['IP Address'] = ip
        target_list[index]['HostName'] = ""
    models = []
    arr = {}
    sys_count = 0

    try:
        response = REST_OBJ.get('/redfish/v1/UpdateService/FirmwareInventory')
        data = response.dict
        for oid1 in data[u'Members']:
            api1 = oid1.get('@odata.id')
            req1 = REST_OBJ.get(api1)
            data1 = req1.dict
            value1 = data1[u'Name']
            value2 = data1[u'Version']
            if not discovery:
                if all:
                    arr[value1 + " Ver"] = value2
                elif 'BIOS' in value1.upper() or 'BMC' in value1.upper() or search("BIOS", value1.upper()):
                    if not search("VBIOS", value1.upper()):
                        arr[value1 + " Ver"] = value2
                    if inventory:
                        target_list[index].update(arr)

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
                        if "IPv4Addresses" in data5 and "HostName" in data5:
                            if target_list[index]['IP Address'] == "" and data5["HostName"]!=target_list[index]['HostName']:
                                found=False
                            elif target_list[index]['IP Address'] == "" and data5["HostName"]==target_list[index]['HostName']:
                                target_list[index]['IP Address'] = data5["IPv4Addresses"][0]["Address"]
                                if target_list[index]['IP Address']  not in IP_HostName.keys():
                                    IP_HostName[target_list[index]['IP Address']] = target_list[index]['HostName']                  
                                found=True
                            elif  target_list[index]['IP Address'] != "" and data5["IPv4Addresses"][0]["Address"]==target_list[index]['IP Address']:
                                target_list[index]['HostName'] = data5["HostName"]
                                if target_list[index]['IP Address']  not in IP_HostName.keys():
                                    IP_HostName[target_list[index]['IP Address']] = target_list[index]['HostName']
                                
                                found=True
                        if found:break
                    if found:break
                if found:break
            if not found:
                print("ERROR: Invalid HostName ",target_list[index]['HostName']," is passed. It should be a valid hostname as reported by the DNS")
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
            models.insert(sys_count, model)
            arr[model_info] = models[sys_count]
            sys_count += 1
        target_list[index]["Model"] = model
    except:
        traceback.print_exc()
        print("WARNING: Error in getting Systems details for "+ip)
    REST_OBJ.logout()

#finds HostName for corresponding IP addresss from target_list and vice versa
def find_in_target_list(find_HostName, find_IP, ip, target_list):
    if find_HostName:
        for v in target_list.values():
            if "HostName" in v and v["IP Address"]==ip:
                return v["HostName"]
    if find_IP:
        for v in target_list.values():
            if "IP Address" in v and v["HostName"]==ip:
                return v["IP Address"]
        

#Gets Status Details after Firmware Update
def UpdateDetails(ip, update_list, login_username, login_password, Pre_Ver, Model,Update_Nature,target,bmc_success_status,bios_success_status,chassis_reset_status,system_reset_status):
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
        update_list[index]['HostName'] = ip
        find_HostName = False
        find_IP = True
        update_list[index]['IP Address'] = find_in_target_list(find_HostName, find_IP, ip, target_list)
        #print("IP Address", update_list[index]['IP Address'])
    else:
        update_list[index]['IP Address'] = ip
        find_HostName = True
        find_IP = False
        update_list[index]['HostName'] = find_in_target_list(find_HostName, find_IP, ip, target_list)
        #print("hostName: " + str(update_list[index]['HostName']))
    #print(update_list)
    try:
        response = REST_OBJ.get('/redfish/v1/UpdateService/FirmwareInventory/'+target)
        data = response.dict
        Post_Ver = data[u'Version']
        if Post_Ver != Pre_Ver and Update_Nature == "Not Same":
            Status = "Success"
        elif Update_Nature == "Same" and Post_Ver == Pre_Ver:
            if target == "BMC":
                if ip in bmc_success_status:
                    Status = "Success"
                else:
                    Status = "Fail"
            if target == "BIOS":
                if ip in bios_success_status and ip in chassis_reset_status and ip in system_reset_status:
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
    IP_HostNames = []
    for line in lines:
        if not line.startswith('#'):
            IP_HostName = line.split(delimiter)[0]
            try:
                if  IP_HostName not in IP_HostNames:
                    IP_HostNames.append(IP_HostName)
                else:
                    print("ERROR: Duplicate entries for ",IP_HostName, " in " + filename)
                    print("INFO: Only one entry for a system is allowed for the firmware updation")
                    print("Exiting...")
                    return True
            except:
                pass
    return False

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
def update_BMC(update_list, target_list, ip_list, filename,choice_Force):
    bmc_success_status = []
    flag=False
    target_list_copy = {}
    for key in target_list:
        ip_addr = target_list[key]['IP Address']
        if ip_addr in target_list_copy:
            print("INFO:",ip_addr,"and",target_list[key]["HostName"],"must be of a single system only")
            continue
        else:
            target_list_copy[ip_addr] = {"BMC Ver": target_list[key]['BMC Ver'], "Server Model": target_list[key]['Model']}
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
                            print("INFO: Update Proceeding for: "+ip)
                            ip_list[ip]["Pre-Ver"] = existing_Version
                            ip_list[ip]["Model"] = model_ip
                            if existing_Version == firmware_detail[0]:
                                ip_list[ip]["Update_Nature"] = "Same"
                            else:
                                ip_list[ip]["Update_Nature"] = "Not Same"
                            thread = threading.Thread(target = final_bmc, args = (ip, ip_list_cpy[ip]["user"], ip_list_cpy[ip]["password"], bmc_file ,bmc_success_status))
                            thread.start()
                            threads.append(thread)
                            #deleting ip from ip_list_cpy to avoid reiteration
                            del ip_list_cpy[ip]
                        else:
                            print("WARNING: Update is halted because Force argument is not set as the version is same as suggested for: "+ ip )
                    else:
                        print("WARNING: Error in the filename for "+ model_name+" update skipped for "+ip)
            except:
                print("** "+ip+" is not reachable!!!")
                continue


    for thread in threads:
        thread.join()
    fp.close
    if flag:
        print("INFO: Sleeping for 5 minutes, To let BMC reset to happen in the background")
        time.sleep(300)
    threads = []
    for ipadd in ip_list.keys():
        key = "Pre-Ver"
        if key in ip_list[ipadd].keys():
            thread = threading.Thread(target = UpdateDetails, args = (ipadd, update_list, ip_list[ipadd]["user"], ip_list[ipadd]["password"], ip_list[ipadd]["Pre-Ver"], ip_list[ipadd]["Model"],ip_list[ipadd]["Update_Nature"],"BMC",bmc_success_status,[],[],[]))
            thread.start()
            threads.append(thread)
    for thread in threads:
        thread.join()

#update_BIOS is wrapper funtion that parses FirmwareDeploy.txt and ip/hostname along with its credentials
#and calls final_bios function to do update
def update_BIOS(update_list, target_list, ip_list, filename,choice_powercycle,choice_Force):
    flag=False
    reset_list={}
    threads = []
    chassis_reset_status = []
    system_reset_status = []
    bios_success_status = []
    target_list_copy = {}
    for key in target_list:
        ip_addr = target_list[key]['IP Address']
        if ip_addr in target_list_copy:
            print("INFO:",ip_addr,"and",target_list[key]["HostName"],"must be of a single system only")
            continue
        else:
            target_list_copy[ip_addr] = {"BIOS Ver": target_list[key]['BIOS Ver'], "Server Model": target_list[key]['Model']}
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
                            print("INFO: Update Proceeding for: "+ip)
                            ip_list[ip]["Pre-Ver"] = existing_Version
                            ip_list[ip]["Model"] = model_ip
                            if existing_Version == firmware_detail[0]:
                                ip_list[ip]["Update_Nature"] = "Same"
                            else:
                                ip_list[ip]["Update_Nature"] = "Not Same"
                            thread = threading.Thread(target = final_bios, args = (ip, ip_list_cpy[ip]["user"], ip_list_cpy[ip]["password"], bios_file , bios_success_status))
                            thread.start()
                            threads.append(thread)
                            del ip_list_cpy[ip]
                        else:
                            print("WARNING: Update is halted because Force argument is not set as the version is same as suggested for: "+ ip )
                    else:
                        print("WARNING: Error in the filename for "+ model_name+" update skipped for "+ip)
            except:
                print("** "+ip+" is not reachable!!!")
                continue


    for thread in threads:
        thread.join()
    fp.close
    if flag:
        if choice_powercycle:
            for k,val in ip_list.items():
                if len(val)>2 and k in bios_success_status: #only do chassis reset/system reset if bios is flashed successfully
                    reset_list[k]=val
            print("INFO: Sleeping 5 minutes, Working on BIOS Update in the Background")
            #print("reset_list",reset_list)
            time.sleep(300)
            Power_Cycling(reset_list,chassis_reset_status,system_reset_status)
            print("INFO: Sleeping 5 minutes allow Power-Cycle to complete and Update to Reflect")
            time.sleep(300)
            threads = []
            for ipadd in ip_list.keys():
                key = "Pre-Ver"
                if key in ip_list[ipadd].keys():
                    thread = threading.Thread(target = UpdateDetails, args=(ipadd, update_list, ip_list[ipadd]["user"], ip_list[ipadd]["password"], ip_list[ipadd]["Pre-Ver"],ip_list[ipadd]["Model"],ip_list[ipadd]["Update_Nature"],"BIOS",[],bios_success_status,chassis_reset_status,system_reset_status))
                    thread.start()
                    threads.append(thread)
            for thread in threads:
                thread.join()
        else:
            print("INFO: The version changes for BIOS will not be reflected unless we complete an Chassis reset and System reset")
            print("INFO: Please do the same for the BIOS version change, It may take around few minutes for version to reflect ")
            print("INFO: Perform Inventory report to know the status")
            print("INFO: Exiting")
            sys.exit()

description_Details_v1 = """
This program is designed to:

1.Discover which server nodes are part of the HPC population and
  provide a report of the node: model, hostname, and IP address
2.Create an Inventory report of HPC population to include a list
  of model type, hostname, IP address, and firmware versions of
  all components which the tool can manage
3.Update BMC and BIOS

To generate Discovery and Inventory reports, list.txt which is a
default file can be used, any other file can also be used with -f
option.
Only text file and csv file are processed to generate reports.
Column name of CSV files should be IP,User and Password.
For Text file "#" can be used for comment and IP/Hostname,User details
and password are to be seperated by ";"
If all the nodes have same user name and password -u and -p can be used
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
    parser.add_argument('-t', '--target', action='store', help='''Target IP Address/Hostnames for report or Update.
Multiple Modes:
    -t IP,UNAM,PWD - to specify a single target.
    -t prompt - prompts for IP,UNAM,PWD of one target
    -t promptall - prompts for UNAM,PWD for all chassis from the file,default is list.txt.
    -t IP,prompt - prompt for UNAM,PWD for one target.
                        ''')
    parser.add_argument('-f', '--filename', action='store', help='''file consisting of IP Addresses/Hostnames (Necessary),username (Optional) and password
(Optional) seperated by ';' for reports, default is list.txt. If this file has only IP address,
they can be listed in different lines
            ''' )
    parser.add_argument('-db','--database', action='store_true', help='''To be set if the credentials of IP Addresses/Hostnames present in the input file to be extracted from database''')
    parser.add_argument('-c', '--component', action='store', help='''Component for Update.
Multiple Modes:
    -c BMC - to choose BMC Update.
    -c BIOS - to choose BIOS Update
                           ''')
    parser.add_argument('-P', '--Power', action='store_true', help="Applies AC Power Cycles when required for update,if not applied the updates will not be reflected")
    parser.add_argument('-F', '--Force', action='store_true', help="Forces install when version to be updated is same the existing version.")
    parser.add_argument('-a', '--all', action='store_true', help="It shows all Firmware details")
    parser.add_argument('-d', '--discovery', action='store_true', help="Node Discovery Report displays IP Address, HostName and ServerModel of HPC cluster")
    parser.add_argument('-i', '--inventory', action='store_true', help="Node Inventory Report displays IP Address, HostName, ServerModel, BIOS Ver and BMC Ver of HPC cluster")
    parser.add_argument('-z', '--update', action='store_true', help="Firmware Update")
    parser.add_argument('-v', action='version')

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
            print("INFO: Extracting Credentials from database for IP Address/HostName's in input text file")
            ip_list = database_Processing(filename)
        else:
            print("INFO: No session password and session username common to all nodes was passed as arguments, Parsing the file ")
            ip_list = file_Processing(filename)
        #Report or Update
        if(args.all or args.discovery or args.inventory):
            for ipadd in ip_list.keys():
                thread = threading.Thread(target = get_FirmwareInventory, args=(ipadd, target_list, ip_list[ipadd]["user"], ip_list[ipadd]["password"], args.all, args.discovery, args.inventory))
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
                df = pd.DataFrame.from_dict({i: new_target_list[i]
                for i in new_target_list.keys()},
                    orient='index')
                df = df.rename_axis("Sl No")
                df.reset_index(inplace=True)
                df = df.sort_values(by = ['HostName'])
                df = df.sort_values(by=['IP Address'])
                df.style.set_properties(**{'text-align': 'right'})
                df.sort_index(axis=0)
                df['Sl No'] = df['Sl No'].sort_values(ascending=True).tolist()
                df2 = df.to_string(index=False)
                print(df2)
                output_Save(report_name,"report",df)
        elif args.update: #only when --z is given, actual update happens and only Inventory report is generated
            fp = open(filename, 'r')
            lines = fp.readlines()
            if filename.endswith(".txt"):
                delimiter= ";"
            else:
                delimiter=","
            is_duplicate = False
            is_duplicate = target_duplicates(filename, lines, delimiter)
            if is_duplicate:
                sys.exit()
            if len(ip_list)>64:
                print("INFO: Only first 64 IP Address/HostNames are being processed!!!")
                ip_list = ip_list[:64]
            for ipadd in ip_list.keys():
                thread = threading.Thread(target=get_FirmwareInventory, args=(ipadd, target_list, ip_list[ipadd]["user"], ip_list[ipadd]["password"], False, False, True))
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join()

            print("HPE Firmware Update")
            print()
            comp=""
            comp=args.component
            if comp:
                if comp.upper() == "BMC":
                    firmware_Type = "a"
                elif comp.upper() == "BIOS":
                    firmware_Type = "b"
                else:
                    pass
            else:
                print("Enter the type of firmware to Update, Choose A/a or B/b" )
                firmware_Type = input("A)BMC B)BIOS \n")
            if(firmware_Type.lower() =="a"  ):
                print("INFO: BMC Update Selected")
                update_BMC(update_list, target_list, ip_list, "FirmwareToDeploy.txt",args.Force)
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
                update_BIOS(update_list,target_list,ip_list,"FirmwareToDeploy.txt",args.Power,args.Force)
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


