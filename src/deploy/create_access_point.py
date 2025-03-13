import subprocess
import json
import re

def validate_id(client_id):
    if not re.match("^[a-zA-Z0-9]+$", client_id):
        raise ValueError("ID should be alphanumeric without any special characters.")
    return True

def get_existing_access_point(client_id):
    try:
        print("Checking if Access Point already exists...")
        result = subprocess.run(["aws", "efs", "describe-access-points", "--query", "AccessPoints[?ClientToken=='{}']".format(client_id), "--output", "json"], capture_output=True, text=True, check=True)
        json_output = json.loads(result.stdout)
        
        if len(json_output) > 0:
            print("Access Point already exists.")
            return json_output[0]
        else:
            print("Access Point does not exist.")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        return None

def create_efs_access_point(client_id):
    existing_access_point = get_existing_access_point(client_id)
    
    if existing_access_point:
        return existing_access_point["AccessPointId"], existing_access_point["AccessPointArn"], existing_access_point["FileSystemId"]
    
    cmd = [
        "aws", "efs", "create-access-point",
        "--file-system-id", "fs-07ab59687408a6326",
        "--client-token", client_id,
        "--root-directory", "Path=/mlflow/ap-{},CreationInfo={{OwnerUid=0,OwnerGid=11,Permissions=777}}".format(client_id),
        "--posix-user", "Uid=22,Gid=4",
        "--tags", "Key=Name,Value={}".format(client_id)
    ]
    
    try:
        print("Creating EFS Access Point...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        json_output = json.loads(result.stdout)
        
        access_point_id = json_output.get("AccessPointId", None)
        access_point_arn = json_output.get("AccessPointArn", None)
        file_system_id = json_output.get("FileSystemId", None)
        
        if all([access_point_id, access_point_arn, file_system_id]):
            print("Access Point Created Successfully!")
            return access_point_id, access_point_arn, file_system_id
        else:
            print("Some information was not found in the response.")
            return None, None, None
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        return None, None, None

def main():
    client_id = input("Please enter a unique alphanumeric ID: ")
    
    try:
        validate_id(client_id)
        
        access_point_id, access_point_arn, file_system_id = create_efs_access_point(client_id)
        
        if all([access_point_id, access_point_arn, file_system_id]):
            print(f"The Access Point ID is: {access_point_id}")
            print(f"The Access Point ARN is: {access_point_arn}")
            print(f"The File System ID is: {file_system_id}")
            
    except ValueError as e:
        print(f"Validation Error: {e}")

if __name__ == "__main__":
    main()

