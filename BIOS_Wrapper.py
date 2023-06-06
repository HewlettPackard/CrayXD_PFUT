from XD295v_XD220v_XD225v.Bios_Update import flash_bios as v1
from XD670.Bios_Update import flash_bios as v2

def call_bios_function(BMC_IP,USER,PWD,BIOS_HPM,bios_success_status,Model,choice_Debug):
    if Model == "HPE Cray XD295v" or Model == "HPE Cray XD220v" or Model == "HPE Cray XD225v":
        v1(BMC_IP,USER,PWD,BIOS_HPM,bios_success_status,choice_Debug)
    elif Model == "HPE Cray XD670" :
        v2(BMC_IP,USER,PWD,BIOS_HPM,bios_success_status,choice_Debug)
    else:
        print("INFO: Update support not present for "+Model)

