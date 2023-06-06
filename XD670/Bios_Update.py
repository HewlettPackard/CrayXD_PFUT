import time
import redfish
import sys
import json
import threading

global flashed_count
flashed_count = 0

lock = threading.Lock()

def print_flash(flashed_count):
    print("INFO: Cray XD670:",flashed_count,"Done")

def flash_bios(BMC_IP,USER,PWD,BIOS_HPM,bios_success_status,choice_Debug):
    headers = {'Expect': 'Continue','Content-Type': 'multipart/form-data'}
    body = {}
    body['UpdateParameters'] = (None, json.dumps({'Targets': ['/redfish/v1/UpdateService/FirmwareInventory/BIOS']}), 'application/json')
    body['UpdateFile'] = (BIOS_HPM, open(BIOS_HPM, 'rb'),'application/octet-stream' )
    body['OemParameters'] = (None, json.dumps({"ImageType":"HPM_BIOS"}) , 'application/json')
   
    try:
        REST_OBJ = redfish.redfish_client(base_url='https://'+BMC_IP, username=USER, password=PWD, default_prefix='/redfish/v1')
        REST_OBJ.login(auth="session")
    except Exception:
        print("ERROR: Opening session to %s" % BMC_IP)
        print(sys.exc_info())
        return

    try:
        response = REST_OBJ.post('/redfish/v1/UpdateService/upload', body=body, headers=headers)
        print("INFO: BIOS Update v2.1 proceeding for ",BMC_IP,"and Firmware is preparing now, Do not cancel process ****")
        print("INFO: Sleeping for 200 seconds for CrayXD670 to prepare flash area, update file and verify firmware",BMC_IP )
        time.sleep(200)
        global flashed_count
       
        for i in range(1,300):
            time.sleep(1)
                

        lock.acquire()
        flashed_count+=1
        print_flash(flashed_count)
        lock.release()

        if choice_Debug:
            print("DEBUG: %s BIOS update completed."%BMC_IP)
        bios_success_status.append(BMC_IP)

        print("**** INFO: Following setups have successfully completed the BIOS update: ",end="")
        print(", ".join(bios_success_status))

        try:
            REST_OBJ.logout()
        except:
            pass
    except:
        print("ERROR: POST call to Upload details on UpdateService for", BMC_IP)

   
