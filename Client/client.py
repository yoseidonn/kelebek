import requests, json
import os, sys, dotenv, platform, pyudev, subprocess


dotenv.load_dotenv()
#SERVER = os.getenv("SERVER_IP")
SERVER = "http://localhost:8000/rest_api/validate/"

def get_disk_serial_number():
    system = platform.system()
    if system == 'Windows':
        return get_disk_serial_number_windows()
    elif system == 'Linux':
        return get_disk_serial_number_linux()
    elif system == 'Darwin':
        return get_disk_serial_number_mac()
    else:
        return None

def get_disk_serial_number_windows():
    command = 'wmic diskdrive get serialnumber'
    output = subprocess.check_output(command, shell=True, text=True)
    serial_numbers = [line.strip() for line in output.split('\n') if line.strip()]
    return serial_numbers[1] if len(serial_numbers) > 1 else None

def get_disk_serial_number_linux():
    context = pyudev.Context()
    for device in context.list_devices(subsystem='block'):
        if device.device_type == 'disk':
            try:
                serial_number = device.get('ID_SERIAL_SHORT')
                if serial_number:
                    return serial_number
            except (KeyError, OSError):
                pass
    return None

def get_disk_serial_number_mac():
    # Add macOS-specific method to retrieve disk serial number here
    return None
        
def validate_licence_key(uuid: str = get_disk_serial_number(), key: str = "BLANK"):
    url = SERVER + f"{uuid}/{key}"
    print(url)
    try:
        response = requests.get(url)
        content = response.content.decode()

        data = json.loads(content)
        return data
    
    except Exception as e:
        data = {"Status-Code": 1000, "Error-Message": str(e)}
        return data


"""
CODES:
123 Not implemented

700 Succesfully created tables
701 Error occured while creating tables
702 Table not found

800 Key successfully registed
801 Error occured while registering key

900 Licence verified
901 Wrong UUID to licence
904 Error occured

910 Licence has expired
911 Licence key is used in another computer
920 Invalid licence

1000 Network error
1001 No internet
"""

if __name__ == "__main__":
    data = validate_licence_key(uuid=get_disk_serial_number(),key="1234-5678-9012-3456")
    print(data)