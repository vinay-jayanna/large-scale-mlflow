from deploy.create_access_point import create_efs_access_point 
import yaml
import subprocess
import json

def apply_yaml_and_get_details(unique_id):
    # Apply the YAML
    yaml_file = f"mlflow-apefs-{unique_id}.yaml"
    subprocess.run(["kubectl", "apply", "-f", yaml_file])

    # Get the Knative Service details in JSON format
    cmd = ["kubectl", "get", "ksvc", f"ap-efs-mlflow-{unique_id}-server", "-n", "mlflow", "-o", "json"]
    ksvc_details = subprocess.check_output(cmd)
    ksvc_json = json.loads(ksvc_details)

    # Extract required details
    name = ksvc_json["metadata"]["name"]
    url = ksvc_json["status"].get("url", "N/A")  # It might take some time for the URL to be available
    labels = ksvc_json["metadata"].get("labels", {})

    # Print and return the details
    print(f"Name: {name}")
    print(f"URL: {url}")
    print(f"Labels: {labels}")

    return {
        "Name": name,
        "URL": url,
        "Labels": labels
    }




def generate_yaml(
    unique_id, file_system_id, access_point_id, access_point_arn, file_system_arn
):
    knative_service = [
        {
            "apiVersion": "v1",
            "kind": "PersistentVolume",
            "metadata": {
                "name": f"ap-efs-mlflow-{unique_id}-pv",
                "labels": {
                    "type": f"ap-efs-mlflow-{unique_id}-pv",
                },
            },
            "spec": {
                "capacity": {"storage": "10Gi"},
                "volumeMode": "Filesystem",
                "accessModes": ["ReadWriteMany"],
                "persistentVolumeReclaimPolicy": "Retain",
                "storageClassName": "efs-sc",
                "csi": {
                    "driver": "efs.csi.aws.com",
                    "volumeHandle": f"{file_system_id}::{access_point_id}",
                },
            },
        },
        {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"ap-efs-mlflow-{unique_id}-pvc",
                "namespace": "mlflow",
            },
            "spec": {
                "selector": {"matchLabels": {"type": f"ap-efs-mlflow-{unique_id}-pv"}},
                "storageClassName": "efs-sc",
                "accessModes": ["ReadWriteMany"],
                "resources": {"requests": {"storage": "5Gi"}},
            },
        },
        {
            "apiVersion": "serving.knative.dev/v1",
            "kind": "Service",
            "metadata": {
                "name": f"ap-efs-mlflow-{unique_id}-server",
                "namespace": "mlflow",
                "labels": {
                    "FileSystemId": file_system_id.split(":")[-1],  # last part of ARN,
                    "AccessPointId": access_point_id.split(":")[-1],  # last part of ARN

                }
            },
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "autoscaling.knative.dev/class": "kpa.autoscaling.knative.dev",
                            "autoscaling.knative.dev/max-scale": "1",
                            "autoscaling.knative.dev/metric": "rps",
                            "autoscaling.knative.dev/min-scale": "0",
                            "autoscaling.knative.dev/scale-to-zero-pod-retention-period": "1m5s",
                            "autoscaling.knative.dev/target": "15",
                            "autoscaling.knative.dev/terminationGracePeriodSeconds": "60",
                            "AccessPointARN": access_point_arn,
                            "FileSystemARN": file_system_arn,
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "image": "public.ecr.aws/y2o2u1i0/mlflow-ecr:latest",
                                "ports": [{"containerPort": 5000}],
                                "env": [
                                    {
                                        "name": "MLFLOW_BACKEND_STORE_URI",
                                        "value": "file:///main/mlflow/mlruns",
                                    }
                                ],
                                "resources": {
                                    "limits": {"cpu": "2", "memory": "5Gi"},
                                    "requests": {"cpu": "0.1", "memory": "100Mi"},
                                },
                                "volumeMounts": [
                                    {
                                        "name": "efs-mlflow-volume",
                                        "mountPath": "/main/mlflow",
                                    }
                                ],
                            }
                        ],
                        "volumes": [
                            {
                                "name": "efs-mlflow-volume",
                                "persistentVolumeClaim": {
                                    "claimName": f"ap-efs-mlflow-{unique_id}-pvc"
                                },
                            }
                        ],
                        "timeoutSeconds": 60,
                    },
                }
            },
        },
    ]

    with open(f"mlflow-apefs-{unique_id}.yaml", "w") as file:
        yaml.dump_all(knative_service, file, default_flow_style=False)




def create_mlflow(unique_id):
    (
        access_point_id,
        access_point_arn,
        file_system_id,
    ) = create_efs_access_point(unique_id)  # Assume this function exists and works

    if all([access_point_id, access_point_arn, file_system_id]):
        generate_yaml(
            unique_id, file_system_id, access_point_id, access_point_arn, file_system_id
        )
        print("Knative service YAML has been generated.")

        service_details = apply_yaml_and_get_details(unique_id)
        print(f"Service details: {service_details}")
        return service_details
    else:
        print("Failed to create or retrieve the Access Point.")
        return f"Failed to create or retrieve the Access Point."

def main():
    unique_id = input("Enter a unique alphanumeric ID: ")
    create_mlflow(unique_id)

if __name__ == "__main__":
    main()







