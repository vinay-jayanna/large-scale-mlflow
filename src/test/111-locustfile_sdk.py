import json
import os
import random

from locust import HttpUser, task, between
from locust import HttpUser, task, between, events

from datetime import datetime
import time
import mlflow
from pathlib import Path
from mlflow.exceptions import MlflowException


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
            mlflow.set_tracking_uri(self.client.base_url) 
            print(f"mlflow set tracking uri to: {mlflow.get_tracking_uri()}")

            print(f"Base URL set to: {self.client.base_url}")
            self.server_name = random_server['name']
            print(f"Server name set to: {self.server_name}")

        else:
            self.client.base_url = self.host
            mlflow.set_tracking_uri(self.client.base_url) 
            print(f"Base URL set to: {self.client.base_url}")
            print(f"mlflow set tracking uri to: {mlflow.get_tracking_uri()}")
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
    def create_get_experiment_sdk(self):
        try:
            # Try to create an experiment with a fixed name
            experiment_name = f"{self.server_name}_Experiment_Name_{self.current_time}"
            # experiment_name = "Experiments_sdk"
            
            experiment_id = mlflow.create_experiment(
                experiment_name,
                tags={"version": "v1", "priority": "P1"}
            )
            
            experiment = mlflow.get_experiment(experiment_id)
            print(f"Name: {experiment.name}")
            print(f"Experiment_id: {experiment.experiment_id}")
            print(f"Tags: {experiment.tags}")
            print(f"Lifecycle_stage: {experiment.lifecycle_stage}")
            print(f"Creation timestamp: {experiment.creation_time}")

            if experiment_id:
                print(f"Successfully created an experiment with ID: {experiment_id}")
                self.experiment_id = experiment_id

        except MlflowException as e:
            if "Experiment '{}' already exists.".format(experiment_name) in str(e):
                # If the exception is about the experiment already existing, we consider it a pass.
                print(f"Experiment {experiment_name} already exists, which is expected.")
                print(f"{e}")
                existing_experiment = mlflow.get_experiment_by_name(experiment_name)
                self.experiment_id = existing_experiment.experiment_id
                print(f"Using existing experiment with ID: {self.experiment_id}")
            else:
                print(f"An unexpected MlflowException occurred: {e}")
                events.request_failure.fire(
                    request_type="mlflow",
                    name="create_get_experiment_sdk",
                    response_time=0,
                    exception=str(e)
                )
        except Exception as e:
            print(f"An exception occurred: {e}")
            events.request_failure.fire(
                request_type="mlflow",
                name="create_get_experiment_sdk",
                response_time=0,
                exception=str(e)
            )


    @task()
    def create_run(self):
        headers = {'Content-Type': 'application/json'}
        
        # Check if we have a valid experiment_id
        if not hasattr(self, 'experiment_id'):
            print("No experiment_id available. Skipping create_run.")
            return
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
                    print(f"Successfully created a run with ID: {self.run_id}")
                    response.success()
                else:
                    print("Failed to create a run")
                    response.failure("Failed to create a run")


    @task()
    def log_metric(self):
        headers = {'Content-Type': 'application/json'}

        # Check if we have a valid run_id
        if not hasattr(self, 'run_id'):
            print("No run_id available. Skipping log_metric.")
            return

        # Generate a timestamp in milliseconds
        current_timestamp = int(time.time() * 1000)
        unique_metric_name = f"{self.server_name}_Metric_Name_{self.current_time}"

        payload = {
            "run_id": self.run_id,
            "key": unique_metric_name,
            "value": 0.95,
            "timestamp": current_timestamp,
            "step": 1
        }

        with self.client.post("/api/2.0/mlflow/runs/log-metric",
                              data=json.dumps(payload),
                              headers=headers,
                              catch_response=True) as response:

            if response.status_code != 200:
                print(f"Failed to get a valid response: {response.status_code}")
                print(f"Response text: {response.text}")
                response.failure("Got wrong response")
            else:
                print(f"Successfully logged a metric for run_id: {self.run_id}")
                response.success()