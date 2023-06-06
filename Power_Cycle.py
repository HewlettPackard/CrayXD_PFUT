import time
import redfish
import threading

#debug=True
debug=False
system_reset_failed=[]
chassis_reset_failed=[]

def system_reset(BMC_IP,USER,PWD,system_reset_status,choice_Debug):
    task_status = ""
    try:
        REST_OBJ = redfish.redfish_client(base_url='https://'+BMC_IP, username=USER, password=PWD, default_prefix='/redfish/v1')
        REST_OBJ.login(auth="session")
        body = {"ResetType": "ForceRestart"}
        response = REST_OBJ.post("/redfish/v1/Systems/Self/Actions/ComputerSystem.Reset", body=body)
        if debug:print("response: %s" % response)
        response_final = response.dict
        if debug:print("response_final: %s" % response_final)
        Task = response_final["@odata.id"]
        if debug:print("Task: %s" % Task)
        Task_response = REST_OBJ.get(Task)
        if debug: print("response: %s" % Task_response)
        task_status_dict = Task_response.dict
        if debug: print("task_status_dict: %s",task_status_dict)
        task_status = task_status_dict["TaskState"]
        if debug:print("task_status: %s" % task_status)
        
        count = 0
        while(task_status != "Completed" and count < 120):
            try:
                task_status_dict = REST_OBJ.get(Task).dict
                if debug: print("task_status_dict: %s",task_status_dict)
                task_status = task_status_dict["TaskState"]
                if debug:print("task_status: %s" % task_status)
            except:
                if count%60==0:
                    if debug:
                        print("ERROR: Failed in GET call of Task API to Computer.Reset for", BMC_IP)
                else:pass
                
            time.sleep(10)
            count += 10

    except Exception:
        #print("Error opening session to %s" % BMC_IP, end='     ')
        #print(sys.exc_info())
        if choice_Debug:
            print("DEBUG: System Reset failed for", BMC_IP)
        system_reset_failed.append(BMC_IP)
        return


    if (task_status != "Completed"):
        if choice_Debug:
            print("DEBUG: Failed System Reset of " + BMC_IP)
        system_reset_failed.append(BMC_IP)
    else:
        if choice_Debug:
            print("DEBUG: System Reset successful for "+ BMC_IP)
        system_reset_status.append(BMC_IP)
        
    try:
        REST_OBJ.logout()
    except:
        pass

def chassis_reset(BMC_IP,USER,PWD,chassis_reset_status,choice_Debug):
    try:
        task_status = ""
        count = 0
        REST_OBJ = redfish.redfish_client(base_url='https://'+BMC_IP, username=USER, password=PWD, default_prefix='/redfish/v1')
        REST_OBJ.login(auth="session")
        body = {"ResetType": "ForceRestart"}
        response = REST_OBJ.post("/redfish/v1/Chassis/Self/Actions/Chassis.Reset", body=body)
        if debug:print("response: %s" % response)
        response_final = response.dict
        if debug:print("response_final: %s" % response_final)
        Task = response_final["@odata.id"]
        if debug:print("Task: %s" % Task)
        Task_response = REST_OBJ.get(Task)
        if debug:print("Task_response: %s" % Task_response)
        task_status_dict = Task_response.dict
        if debug:print("task_status_dict: %s" % task_status_dict)
        task_status = task_status_dict["TaskState"]
        if debug:print("task_status: %s" % task_status)

        while(task_status != "Completed" and count < 120):
            try:
                task_status_dict = REST_OBJ.get(Task).dict
                task_status = task_status_dict["TaskState"]
            except:
                if count%60==0:
                    if debug:
                        print("ERROR: Failed in GET call of Task API to Chassis.Reset for", BMC_IP)
                else:
                    pass
                
            time.sleep(10)
            count += 10
    except Exception:
        #print("Error opening session to %s" % BMC_IP, end='     ')
        #print(sys.exc_info())
        if choice_Debug:
            print("DEBUG: Chassis Reset failed for", BMC_IP)
        chassis_reset_failed.append(BMC_IP)
        return


    if (task_status != "Completed"):
        if choice_Debug:
            print("DEBUG: Failed Chassis Reset of " + BMC_IP)
        chassis_reset_failed.append(BMC_IP)
    else:
        if choice_Debug:
            print("DEBUG: Chassis Reset successful for "+ BMC_IP)
        chassis_reset_status.append(BMC_IP)

    try:
        REST_OBJ.logout()
    except:
        pass

def Power_Cycling(reset_list,chassis_reset_status,system_reset_status,choice_Debug):   
    
    print("INFO: Performing System Reset in background. Please wait for some time to know the status of System Reset.")
    threads = []
    for ipadd in reset_list.keys():
            thread = threading.Thread(target = system_reset, args=(ipadd, reset_list[ipadd]["username"], reset_list[ipadd]["password"],system_reset_status,choice_Debug))
            thread.start()
            threads.append(thread)
    for thread in threads:
            thread.join()    
        
    time.sleep(120)

    print("INFO: Performing Chassis Reset in background. Please wait for some time to know the status of Chassis Reset.")
    threads = []
    for ipadd in reset_list.keys():
            thread = threading.Thread(target = chassis_reset, args=(ipadd, reset_list[ipadd]["username"], reset_list[ipadd]["password"],chassis_reset_status,choice_Debug))
            thread.start()
            threads.append(thread)
    for thread in threads:
            thread.join()
    
    if len(system_reset_status)>0:
        print("**** INFO: System reset SUCCESS for ",end='')
        print(", ".join(system_reset_status))
    if len(system_reset_failed)>0:
        print("**** INFO: System reset FAILURE for ",end='')
        print(", ".join(system_reset_failed))
    if len(chassis_reset_status)>0:
        print("**** INFO: Chassis reset SUCCESS for ",end='')
        print(", ".join(chassis_reset_status))
    if len(chassis_reset_failed)>0:
        print("**** INFO: Chassis reset FAILURE for ",end='')
        print(", ".join(chassis_reset_failed))

