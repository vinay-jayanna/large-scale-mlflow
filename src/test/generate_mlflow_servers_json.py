import json

# Define the base URL and name format
base_url = "http://pg-mlflow-{i}.mlflow.13.233.56.157.sslip.io"
base_name = "pg-mlflow-{i}"

# Define the number of MLflow servers
number_of_servers = 1000

# Create a list of server dictionaries
servers = [{"url": base_url.format(i=i), "name": base_name.format(i=i)} for i in range(1, number_of_servers + 1)]

# Convert the list of servers to a JSON formatted string
json_servers = json.dumps(servers, indent=4)

# Write the JSON string to a file
with open('mlflow_servers.json', 'w') as f:
    f.write(json_servers)

print(f"mlflow_servers.json file has been generated with {number_of_servers} servers.")
