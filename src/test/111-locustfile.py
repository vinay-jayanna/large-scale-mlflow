import json
import os
import random

from locust import HttpUser, task, between

from datetime import datetime
import time
import mlflow
from pathlib import Path
import requests 


class MLflowUser(HttpUser):
    host = "http://dummy-host"
    wait_time = between(5, 15)
    server_configs = []  # Class variable

    @classmethod
    def fetch_mlflow_servers(cls):  # Class method
        if not cls.server_configs:  # Only read the file if server_configs is empty
            with open('mlflow_servers.json', 'r') as f:
                cls.server_configs = json.load(f)
                print(f"Loaded {len(cls.server_configs)} MLflow servers") 
                print(f"Server configs: {cls.server_configs}")


    def on_start(self):
        self.current_time = datetime.now().strftime("%Y%m%d%H%M")
        # Fetch servers only once and store them in the class variable
        self.fetch_mlflow_servers()

        if self.host == "http://dummy-host":
            if not self.server_configs:
                print("No MLflow servers found. Exiting.")
                exit(1)

            random_server = random.choice(self.server_configs)
            self.client.base_url = random_server['url']
            print(f"Base URL set to: {self.client.base_url}")
            self.server_name = random_server['name']
            print(f"Server name set to: {self.server_name}")

        else:
            self.client.base_url = self.host
            self.server_name = self.host.replace("http://", "")[:4]  # Remove 'http://' and take first 4 letters
            print(f"Using command line host: {self.host}")
            print(f"Server name set to: {self.server_name}")


    @task()
    def search_experiment(self):
        headers = {'Content-Type': 'application/json'}
        payload = {"max_results": 10}
        with self.client.post("/api/2.0/mlflow/experiments/search",
                              data=json.dumps(payload),
                              headers=headers,
                              catch_response=True) as response:
            if response.status_code != 200:
                print(f"Failed to get a valid response: {response.status_code}")
                print(f"Response text: {response.text}")
                response.failure("Got wrong response")
            else:
                response.success()


    @task()
    def create_get_experiment(self):
        headers = {'Content-Type': 'application/json'}
        unique_experiment_name = f"{self.server_name}_Experiment_Name_{self.current_time}"

        payload = {
            "name": unique_experiment_name,  
            "tags": [  # Optional, can add tags if needed
                {"key": "tag1", "value": self.server_name + "tag1"},
                {"key": "tag2", "value": self.server_name + "tag2"}
            ]
        }

        with self.client.post("/api/2.0/mlflow/experiments/create",
                              data=json.dumps(payload),
                              headers=headers,
                              catch_response=True) as response:

            if response.status_code == 200:
                response_data = json.loads(response.text)
                experiment_id = response_data.get('experiment_id', None)
                if experiment_id:
                    # print(f"Successfully created an experiment with ID: {experiment_id}")
                    self.experiment_id = experiment_id
                    response.success()
                else:
                    print("Failed to create an experiment")
                    response.failure("Failed to create an experiment")

            elif response.status_code == 400:
                error_response = json.loads(response.text)
                if error_response.get("error_code") == "RESOURCE_ALREADY_EXISTS":
                    # print(f"Experiment already exists: {unique_experiment_name}")
                    
                    # Fetch the existing experiment_id
                    get_experiment_payload = {
                        "experiment_name": unique_experiment_name
                    }
                    # Use Python’s requests library to make the API call
                    url = f"{self.client.base_url}/api/2.0/mlflow/experiments/get-by-name"
                    get_experiment_response = requests.get(url,
                                                       params=get_experiment_payload,
                                                       headers=headers)
                    
                    # get_experiment_response = self.client.get("/api/2.0/mlflow/experiments/get-by-name",
                    #                                        params=get_experiment_payload,
                    #                                        headers=headers)
                    
                    if get_experiment_response.status_code == 200:
                        get_experiment_data = json.loads(get_experiment_response.text)
                        self.experiment_id = get_experiment_data['experiment']['experiment_id']
                        # print(f"Set self.experiment_id to existing experiment ID: {self.experiment_id}")
                    
                    response.success()
                else:
                    print(f"Failed to get a valid response: {response.status_code}")
                    print(f"Response text: {response.text}")
                    response.failure("Got wrong response")
                    
            else:
                print(f"Failed to get a valid response: {response.status_code}")
                print(f"Response text: {response.text}")
                response.failure("Got wrong response")



    @task()
    def create_run(self):
        headers = {'Content-Type': 'application/json'}
        
        # Check if we have a valid experiment_id
        if not hasattr(self, 'experiment_id'):
            # print("No experiment_id available. Trying to create one before create_run.")
            self.create_get_experiment()
            
        unique_run_name = f"{self.server_name}_Run_Name_{self.current_time}"

        payload = {
            "experiment_id": self.experiment_id,
            "run_name": unique_run_name,
            "start_time": int(time.time() * 1000),  # current time in milliseconds
            "tags": [
                {"key": "tag1", "value": "value1"},
                {"key": "tag2", "value": "value2"}
            ]
        }

        with self.client.post("/api/2.0/mlflow/runs/create",
                            data=json.dumps(payload),
                            headers=headers,
                            catch_response=True) as response:

            if response.status_code != 200:
                print(f"Failed to get a valid response: {response.status_code}")
                print(f"Response text: {response.text}")
                response.failure("Got wrong response")
            else:
                response_data = json.loads(response.text)
                run = response_data.get('run', {})
                self.run_id = run.get('info', {}).get('run_id', None)
                if self.run_id:
                    # print(f"Successfully created a run with ID: {self.run_id}")
                    response.success()
                else:
                    print("Failed to create a run")
                    response.failure("Failed to create a run")


    @task()
    def log_metric_and_param(self):
        headers = {'Content-Type': 'application/json'}

        # Check if we have a valid run_id
        if not hasattr(self, 'run_id'):
            # print("No run_id available. trying to create one before log_metric_and_param.")
            self.create_run()

        # Generate a timestamp in milliseconds
        current_timestamp = int(time.time() * 1000)

        for i in range(10):
            # Log metric
            unique_metric_name = f"{self.server_name}_Metric_Name_{self.current_time}_{i}"
            metric_payload = {
                "run_id": self.run_id,
                "key": unique_metric_name,
                "value": 0.95,
                "timestamp": current_timestamp,
                "step": 1
            }
            with self.client.post("/api/2.0/mlflow/runs/log-metric",
                                data=json.dumps(metric_payload),
                                headers=headers,
                                catch_response=True) as response:

                if response.status_code != 200:
                    print(f"Failed to log metric. Response code: {response.status_code}")
                    print(f"Response text: {response.text}")
                    response.failure("Got wrong response")
                else:
                    # print(f"Successfully logged a metric for run_id: {self.run_id}")
                    response.success()

            # Log parameter
            unique_param_name = f"{self.server_name}_Param_Name_{self.current_time}_{i}"
            param_payload = {
                "run_id": self.run_id,
                "key": unique_param_name,
                "value": f"parameter_value_{i}",
            }
            with self.client.post("/api/2.0/mlflow/runs/log-parameter",
                                data=json.dumps(param_payload),
                                headers=headers,
                                catch_response=True) as response:

                if response.status_code != 200:
                    print(f"Failed to log parameter. Response code: {response.status_code}")
                    print(f"Response text: {response.text}")
                    response.failure("Got wrong response")
                else:
                    # print(f"Successfully logged a parameter for run_id: {self.run_id}")
                    response.success()




    @task()
    def log_register_model(self):
        headers = {'Content-Type': 'application/json'}

        # Check if we have a valid run_id
        if not hasattr(self, 'run_id'):
            # print("No run_id available. Trying to create one before log_register_model.")
            self.create_run()

        # Generate a timestamp in milliseconds
        current_timestamp = int(time.time() * 1000)

        unique_model_name = f"{self.server_name}_Model_Name_{current_timestamp}"
        artifact_path = f"s3://s3://vin-postgre-mlflow/models/{unique_model_name}/model.pkl"  # Specify the correct artifact path

        # Log Model to the Run
        log_model_payload = {
            "run_id": self.run_id,
            "model_json": json.dumps({
                "name": unique_model_name,
                "utc_time_created": "2018-05-25T17:28:53.35", # Adjust the time format accordingly
                "run_id": self.run_id,
                "artifact_path": artifact_path, # Adjust the artifact path accordingly
                "flavors": {
                    "sklearn": {
                        "sklearn_version": "0.19.1",
                        "pickled_model": "model.pkl", # Assuming the model file is named "model.pkl" and is located at the root of the artifact URI
                    },
                    "python_function": {
                        "loader_module": "mlflow.sklearn",
                    },
                },
            }),
        }

        with self.client.post("/api/2.0/mlflow/runs/log-model",
                            data=json.dumps(log_model_payload),
                            headers=headers,
                            catch_response=True) as response:

            if response.status_code != 200:
                print(f"Failed to log model {unique_model_name} to run_id: {self.run_id}. Status Code: {response.status_code}")
                print(f"Response text: {response.text}")
                response.failure("Got wrong response")
            else:
                # print(f"Successfully logged model {unique_model_name} for run_id: {self.run_id}")
                response.success()

        # Create Registered Model
        create_model_payload = {
            "name": unique_model_name,
            # Add other fields like 'tags' and 'description' if needed
        }
        with self.client.post("/api/2.0/mlflow/registered-models/create",
                            data=json.dumps(create_model_payload),
                            headers=headers,
                            catch_response=True) as response:

            if response.status_code != 200:
                print(f"Failed to create registered model {unique_model_name}. Status Code: {response.status_code}")
                print(f"Response text: {response.text}")
                response.failure("Got wrong response")
            else:
                # print(f"Successfully created registered model {unique_model_name}")
                response.success()

                    
 



                
            
                