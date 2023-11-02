import time
import redfish
import sys
import json
import threading

global flashed_count
flashed_count = 0

lock = threading.Lock()
    
def obtain_UpdateStatus(redfish_output):
    redfish_output1 = redfish_output.dict
    try:
        data = redfish_output1["Oem"]["AMIUpdateService"]["UpdateStatus"]
    except:
        return None
    return data

#obtain_FlashPercentage is a function that parses through /redfish/v1/UpdateService to obtain FlashPercentage
def obtain_FlashPercentage(redfish_output):
    redfish_output1 = redfish_output.dict
    try:
        data = redfish_output1["Oem"]["AMIUpdateService"]["FlashPercentage"]
    except:
        return None
    return data

def print_flash(flashed_count):
    print("INFO: Cray XD665:",flashed_count,"Done with Flashing 100% Completed  ")

def flash_bios(BMC_IP,USER,PWD,BIOS_HPM,bios_success_status,choice_Debug):
    headers = {'Expect': 'Continue','Content-Type': 'multipart/form-data'}
    body = {}
    body['UpdateParameters'] = (None, json.dumps({'Targets': ['/redfish/v1/UpdateService/FirmwareInventory/BIOS']}), 'application/json')
    body['UpdateFile'] = (BIOS_HPM, open(BIOS_HPM, 'rb'),'application/octet-stream' )
    body['OemParameters'] = (None, json.dumps({"ImageType":"HPM"}) , 'application/json')

    try:
        REST_OBJ = redfish.redfish_client(base_url='https://'+BMC_IP, username=USER, password=PWD, default_prefix='/redfish/v1')
        REST_OBJ.login(auth="session")
    except Exception:
        print("ERROR: Opening session to %s" % BMC_IP)
        print(sys.exc_info())
        return
    
    Status = ""
    LastStatus = ""
    verified = ""
    Update_Status=""
    FlashPercentage=""
    Completed = ""

    try:
        response = REST_OBJ.post('/redfish/v1/UpdateService/upload', body=body, headers=headers)
    except:
        print("ERROR: POST call to Upload details on UpdateService for", BMC_IP)

    print("INFO: BIOS Update v3.1 proceeding for",BMC_IP,"and Firmware is preparing now, Do not cancel process ****")

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
                if choice_Debug:
                    print("DEBUG: "+BMC_IP+" "+Status)        
            LastStatus = Status
        except:
            if i%20==0:
                print("ERROR: Getting UpdateService details for", BMC_IP)
        
        time.sleep(1)
    
    if verified=="Pass":
        if choice_Debug:
            print("DEBUG: "+BMC_IP+" Firmware is flashing now")
        for i in range(1,100):
            try:
                cmd_result = REST_OBJ.get('/redfish/v1/UpdateService')
                FlashPercentage = obtain_FlashPercentage(cmd_result)
                if FlashPercentage=="done":
                    verified = "Pass"
                    break
            except:
                if i%20==0:
                    print("ERROR: Getting UpdateService details for", BMC_IP)
            
            time.sleep(1)
    else:
        time.sleep(180)
    global flashed_count

    for i in range(1,300):
        try:
            cmd_result = REST_OBJ.get('/redfish/v1/UpdateService')
            FlashPercentage = obtain_FlashPercentage(cmd_result)
            Update_Status = obtain_UpdateStatus(cmd_result)
            if FlashPercentage=="100% done." :
                Completed = "Pass"
                lock.acquire()
                flashed_count+=1
                print_flash(flashed_count)
                lock.release()
                break
            if Update_Status=="null":
                Completed = "Pass"
            
        except:
            if i%60==0:
                print("ERROR: Getting UpdateService details for", BMC_IP)
        time.sleep(1)
        
    
    
    time.sleep(10)
    if choice_Debug:
        print("DEBUG: "+BMC_IP+" BIOS update completed.")
    if BMC_IP not in bios_success_status:
        bios_success_status.append(BMC_IP)
        print("**** INFO: Following setups have successfully completed the BIOS update: ",end="")
        print(", ".join(bios_success_status))
    

    #catching exception if occurs when rest object log out fails due to disconnecting session during BMC reset for BIOS upgradation
    try:
        REST_OBJ.logout()
    except:
        pass




