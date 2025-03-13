import streamlit as st
import subprocess
import pandas as pd
import io
import re
from deploy.create_mlflow_ap_server import create_mlflow
import json
from time import sleep
import plotly.express as px
from kubernetes import client, config
import plotly.express as px  # Make sure to import plotly


config.load_kube_config()

# Initialize the API clients
v1 = client.CoreV1Api()
api = client.CustomObjectsApi()


# Utility function to extract numeric values
def extract_value(value):
    if value.endswith('n'):
        return int(value.rstrip('n')) / 1_000_000  # Convert nanocores to cores
    elif value.endswith('m'):
        return int(value.rstrip('m')) / 1_000  # Convert millicores to cores
    elif value.endswith('Mi'):
        return int(value.rstrip('Mi'))  # Memory in MiB
    elif value.endswith('Ki'):
        return int(value.rstrip('Ki')) / 1024  # Convert KiB to MiB
    else:
        return int(value)


def fetch_pod_metrics(namespace='mlflow'):
    pod_list = v1.list_namespaced_pod(namespace)
    pod_names = [pod.metadata.name for pod in pod_list.items]
    metrics = []

    for pod_name in pod_names:
        try:
            resource = api.get_namespaced_custom_object(
                "metrics.k8s.io", "v1beta1", namespace, "pods", pod_name)
            print(f"Resource: {resource}")

            cpu_value = resource['containers'][0]['usage']['cpu']
            mem_value = resource['containers'][0]['usage']['memory']
            
            print(f"Original CPU value for {pod_name}: {cpu_value}")
            print(f"Original Memory value for {pod_name}: {mem_value}")

            cpu_usage = extract_value(cpu_value)
            memory_usage = extract_value(mem_value)
            
            print(f"Extracted CPU value for {pod_name}: {cpu_usage}")
            print(f"Extracted Memory value for {pod_name}: {memory_usage}")

            metrics.append([pod_name, cpu_usage, memory_usage])
            
        except Exception as e:
            print(f"Could not fetch metrics for pod {pod_name}: {e}")

    df = pd.DataFrame(metrics, columns=['Pod', 'CPU', 'Memory'])
    return df


def fetch_pod_metrics_cli():
    command = '''
    kubectl get pods -n mlflow --no-headers -o custom-columns=":metadata.name" | while read -r pod_name; do
        kubectl top pod "$pod_name" -n mlflow --no-headers | awk -v pod="$pod_name" '{ printf "%-25s %-12s %-12s\\n", pod, $2, $3 }'
    done
    '''
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    output = result.stdout.strip().split("\n")

    if len(output) == 0 or (len(output) == 1 and output[0] == ''):
        # Handle the case where there are no pods
        df = pd.DataFrame(columns=['Pod', 'CPU', 'Memory'])
    else:
        df = pd.DataFrame([line.split() for line in output], columns=['Pod', 'CPU', 'Memory'])
        df['CPU'] = df['CPU'].str.rstrip('m').astype(int)  # Assuming CPU is in "millicores", strip 'm' and convert to int
        df['Memory'] = df['Memory'].str.rstrip('Mi').astype(int)  # Assuming Memory is in "MiB", strip 'Mi' and convert to int

    return df


# Streamlit UI
def main():
    st.title("MLflow Management")

    menu = st.sidebar.selectbox(
        'Menu', 
        ['Dashboard', 'Create MLflow']
    )
    if menu == 'Create MLflow':
        workspace_id = st.text_input("Enter Workspace ID")

        workspace_id = workspace_id[:10]  # Limit string length to 10

        if st.button("Launch", type="primary"):
            if workspace_id:
                if not re.match("^[a-z0-9]+$", workspace_id):
                    st.error("Workspace ID should be lower-case alphanumeric only, no special characters.")
                else:
                    with st.spinner('Creating MLflow tracking server...'):
                        mlflow_link = create_mlflow(workspace_id)
                    message = f"""
                    MLflow Tracking server launched successfully.>

                    - **Name**: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {mlflow_link.get('Name', 'N/A')}
                    - **URL**: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [{mlflow_link.get('URL', 'N/A')}]({mlflow_link.get('URL', 'N/A')})
                    - **AccessPointId**: &nbsp; {mlflow_link.get('Labels', {}).get('AccessPointId', 'N/A')}
                    - **FileSystemId**: &nbsp; {mlflow_link.get('Labels', {}).get('FileSystemId', 'N/A')}
                    """

                    st.success(message)
                    st.toast('Hooray - a new MLflow Tracking Server!', icon='🎉')

            else:
                st.error("Please enter a Workspace ID.")

    elif menu == 'Dashboard':
        mlflow_deploy, mlflow_running, mlflow_data_storage, mlflow_metrics = st.tabs(["Deployed Servers", "Running Servers", "Data Storage", "Metrics"])

        # Tab 1: MLflow Tracking Servers Deployed
        with mlflow_deploy:
            kubectl_command1 = "kubectl get ksvc -n mlflow -o custom-columns='NAME:.metadata.name,NAMESPACE:.metadata.namespace,URL:.status.url,READY:.status.conditions[-1].status,LABELS:.metadata.labels'"
            result1 = subprocess.run(kubectl_command1, shell=True, capture_output=True, text=True)
            output1 = result1.stdout.strip()
            df1 = pd.read_csv(io.StringIO(output1), sep='\s+', index_col=False)
            st.info(f"{df1.shape[0]} deployed MLflow-servers (including both active and scaled-to-zero servers) ")
            st.write("List of MLflow Tracking Servers deployed:")
            st.dataframe(df1, width=5000)

        # Tab 2: mlflow_running Table
        with mlflow_running:
            kubectl_command2 = "kubectl get pods -n mlflow -o wide"  # replace with your actual command
            result2 = subprocess.run(kubectl_command2, shell=True, capture_output=True, text=True)
            output2 = result2.stdout.strip()

            if output2:  # Check if output is not empty
                df2 = pd.read_csv(io.StringIO(output2), sep='\s+', index_col=False)
                st.info(f"{df2.shape[0]} currently Active MLflow Servers")
                st.write("List of active Pods in MLflow namespace:")
                st.dataframe(df2, width=5000)
                    
            else:
                st.snow()
                st.warning("No active Pods in MLflow namespace.")
                st.write(pd.DataFrame())  # Show an empty dataframe

        # Tab 3: Storage
        with mlflow_data_storage:
                # List EFS File Systems
            cmd_efs_filesystems = "aws efs describe-file-systems --output json"
            result_efs_filesystems = subprocess.run(cmd_efs_filesystems, shell=True, capture_output=True, text=True)
            json_efs_filesystems = json.loads(result_efs_filesystems.stdout)
            df_efs_filesystems = pd.json_normalize(json_efs_filesystems['FileSystems'])
            st.info(f"{df_efs_filesystems.shape[0]} data storage EFS File-systems under use")
            st.write("List of EFS File Systems:")
            st.dataframe(df_efs_filesystems, width=5000)

            # List EFS Access Points
            cmd_efs_accesspoints = "aws efs describe-access-points --output json"
            result_efs_accesspoints = subprocess.run(cmd_efs_accesspoints, shell=True, capture_output=True, text=True)
            json_efs_accesspoints = json.loads(result_efs_accesspoints.stdout)
            df_efs_accesspoints = pd.json_normalize(json_efs_accesspoints['AccessPoints'])
            st.info(f"{df_efs_accesspoints.shape[0]} data storage EFS Access-points under use")
            st.write("List of EFS Access Points:")
            st.dataframe(df_efs_accesspoints, width=5000)

        # Tab 4: Metrics
        # mlflow_metrics = st.empty()  # Placeholder for the metrics section

        with mlflow_metrics:
            if st.button("Fetch Metrics", type="secondary"):
                with st.spinner('Fetching Metrics...'):
                    df_metrics = fetch_pod_metrics_cli()
                    
                st.subheader("MLflow server Metrics")
                st.dataframe(df_metrics)
                # Create Bubble chart only if df_metrics is not empty
                    
                fig = px.scatter(df_metrics, x="CPU", y="Memory", size="Memory", 
                                color="CPU", color_continuous_scale=["lightblue", "red"],
                                size_max=6, hover_name="Pod", 
                                labels={'CPU': 'CPU (millicores)', 'Memory': 'Memory (MiB)'},
                                title="CPU vs Memory Consumption by Server")
                        
                fig.update_layout(xaxis_title="CPU (millicores)", yaxis_title="Memory (MiB)")
                st.plotly_chart(fig)

        

if __name__ == "__main__":
    main()


