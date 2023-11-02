from XD295v_XD220v_XD225v.Bmc_Update import flash_bmc as v1
from XD670.Bmc_Update import flash_bmc as v2
from XD665.Bmc_Update import flash_bmc as v3

def call_bmc_function(BMC_IP,USER,PWD,BMC_HPM,bmc_success_status,Model,choice_Debug,backup_image):    
    if Model == "HPE Cray XD295v" or Model == "HPE Cray XD220v" or Model == "HPE Cray XD225v":
        v1(BMC_IP,USER,PWD,BMC_HPM,bmc_success_status,choice_Debug)
    elif Model == "HPE Cray XD670":
        v2(BMC_IP,USER,PWD,BMC_HPM,bmc_success_status,choice_Debug, backup_image)
    elif  Model == "HPE Cray XD665":
        v3(BMC_IP,USER,PWD,BMC_HPM,bmc_success_status,choice_Debug)
    else:
        print("INFO: Update support not present for "+Model)