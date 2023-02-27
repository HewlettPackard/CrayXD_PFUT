import time
import redfish
import sys
import json
import threading

global flashed_count
flashed_count = 0

lock = threading.Lock()

def print_flash(flashed_count):
    print("INFO:",flashed_count,"Done  ", end=' ')

    
def obtain_UpdateStatus(redfish_output):
        redfish_output1 = redfish_output.dict
        data = redfish_output1["Oem"]["AMIUpdateService"]["UpdateStatus"]
        return data


#obtain_FlashPercentage is a function that parses through /redfish/v1/UpdateService to obtain FlashPercentage
def obtain_FlashPercentage(redfish_output):
        redfish_output1 = redfish_output.dict
        data = redfish_output1["Oem"]["AMIUpdateService"]["FlashPercentage"]
        return data

def final_bios(BMC_IP,USER,PWD,BIOS_HPM,bios_success_status):
    headers = {'Expect': 'Continue','Content-Type': 'multipart/form-data'}
    body = {}
    body['UpdateParameters'] = (None, json.dumps({'Targets': ['/redfish/v1/UpdateService/FirmwareInventory/BIOS']}), 'application/json')
    body['UpdateFile'] = (BIOS_HPM, open(BIOS_HPM, 'rb'),'application/octet-stream' )
    body['OemParameters'] = (None, json.dumps({"ImageType":"HPM"}) , 'application/json')
    try:
        REST_OBJ = redfish.redfish_client(base_url='https://'+BMC_IP, username=USER, password=PWD, default_prefix='/redfish/v1')
        REST_OBJ.login(auth="session")
    except Exception:
        print("Error opening session to %s" % BMC_IP, end='     ')
        print(sys.exc_info())
        return
    print("INFO: BIOS Update proceeding for ",BMC_IP)
    print("INFO: "+BMC_IP+" "+" BIOS Update v1.1")
    Status = ""
    LastStatus = ""
    verified = ""
    Update_Status=""
    FlashPercentage=""
    Completed = ""
    try:
        response = REST_OBJ.post('/redfish/v1/UpdateService/upload', body=body, headers=headers)
    except:
        print("INFO: Error in POST call to Upload details on UpdateService for ", BMC_IP)

    print("INFO: "+BMC_IP+" "+"**** Firmware is preparing now, Do not cancel process ****\n")

    for i in range(1,100):
        try:
            cmd_result = REST_OBJ.get('/redfish/v1/UpdateService')
            Update_Status = obtain_UpdateStatus(cmd_result)
            if Update_Status=="Flashing":
                verified = "Pass"
                break
            if Update_Status=="Preparing":
                Status = "Preparing"
            if Update_Status=="VerifyingFirmware":
                Status = "VerifyingFirmware"
            if Update_Status=="Downloading":
                Status = "Downloading"   
            if LastStatus!=Status:
                print("INFO: "+BMC_IP+" "+Status)        
            LastStatus = Status
        except:
            print("INFO: Error in getting UpdateService details for ", BMC_IP)
        
        time.sleep(1)
    
    if verified=="Pass":
        print("INFO: "+BMC_IP+" Firmware is flashing now")
        for i in range(1,100):
            try:
                cmd_result = REST_OBJ.get('/redfish/v1/UpdateService')
                FlashPercentage = obtain_FlashPercentage(cmd_result)
                if FlashPercentage=="done":
                    verified = "Pass"
                    break
            except:
                print("INFO: Error in getting UpdateService details for ", BMC_IP)
            
        time.sleep(1)
    
    for i in range(1,300):
        global flashed_count
        try:
            cmd_result = REST_OBJ.get('/redfish/v1/UpdateService')
            FlashPercentage = obtain_FlashPercentage(cmd_result)
            Update_Status = obtain_UpdateStatus(cmd_result)
        except:
            print("INFO: Error in getting UpdateService details for ", BMC_IP)
        
        lock.acquire()
        if i%60==0:
            print("\nINFO:",threading.active_count()-1-flashed_count,"In Progress       ",end=' ')
            print_flash(flashed_count) #includes main thread also so actual-1
        lock.release()

        if FlashPercentage=="100% done." :
            Completed = "Pass"
            flashed_count+=1
            lock.acquire()
            print('\n****',end=' ')
            print_flash(flashed_count)
            lock.release()
            break
        if Update_Status=="null":
            Completed = "Pass"
        time.sleep(1)
    
    if Completed == "Pass":
        print("INFO: "+BMC_IP+' "FlashPercentage":"100% done."')
        time.sleep(10)
        print("\n**** INFO: "+BMC_IP+" BIOS update completed. ****")
        bios_success_status.append(BMC_IP)
    else :
        print("\nINFO: "+BMC_IP+" [Error] Flash Timeout")

    #catching exception if occurs when rest object log out fails due to disconnecting session during BMC reset for BIOS upgradation
    try:
        REST_OBJ.logout()
    except:
        pass



