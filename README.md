# 🚀 Scalable MLflow for Large-Scale AI Experiment Tracking with Knative & Kubernetes

## Overview
This repository provides a **fully serverless, Kubernetes-native MLflow setup** for tracking **AI experiments at scale**, including **LLM fine-tuning** and large-scale **ML model experimentation**. By leveraging **Knative and Kubernetes**, we enable **on-demand, auto-scaled MLflow instances**, handling thousands of experiments across **distributed AI workflows**.

🔥 **Key Features:**
- **Serverless MLflow** – Deploy MLflow tracking servers on-demand with **Knative & Kubernetes**.
- **AWS EFS for Persistent Storage** – Ensures logs, models, and metadata are stored securely and persist across sessions.
- **Massive Scalability** – Simulates **10K simultaneous MLflow instances** across **150 Kubernetes nodes**.
- **Locust Load Testing** – Stress tests MLflow’s ability to **handle thousands of AI experiments in parallel**.
- **Designed for LLM Experimentation** – Optimized for **fine-tuning and tracking large-scale AI model experiments**.
- **Multi-Cloud Ready** – Although tested on **AWS EKS**, it can be adapted to **GKE, AKS, or on-prem K8s clusters**.


---

## 📌 Architecture & Deployment
### **1️⃣ MLflow on Knative & Kubernetes**
- MLflow instances **scale dynamically** using **Knative's event-driven model**.
- Each MLflow instance runs **ephemerally**, but logs are persisted in **AWS EFS**.
- Serverless requests trigger **instant MLflow tracking servers**, reducing compute waste.

### **2️⃣ Persistent Experiment Storage with AWS EFS**
- MLflow artifacts, logs, and model metadata are stored on **AWS Elastic File System (EFS)**.
- Ensures that experiment history remains accessible across **restarts and scale events**.

### **3️⃣ Locust Load Testing for Scale Validation**
- Simulates **10,000 MLflow tracking instances** to test robustness.
- Runs across **150 Kubernetes nodes**, validating large-scale experiment tracking.
- Provides real-time **latency, throughput, and resource utilization metrics**.

---

## 🚀 Quick Start Guide
### **1️⃣ Clone the Repository**
```sh
git clone https://github.com/vinay-jayanna/scalable-mlflow-knative.git
cd scalable-mlflow-knative
```

### **2️⃣ Install Dependencies & Set Up Environment**
```sh
kubectl apply -f src/installs/efs/efs-pv-pvc.yaml
kubectl apply -f src/installs/efs/mlflow-efs-main.yaml
```

### **3️⃣ Deploy MLflow on Kubernetes with Knative**
```sh
kubectl apply -f src/deploy/mlflow-apefs-0001.yaml
kubectl apply -f src/deploy/mlflow-apefs-0002.yaml
```

### **4️⃣ Load Test with Locust**
Run a large-scale test simulating **10K concurrent MLflow instances**:
```sh
locust -f src/test/111-locustfile.py --headless -u 10000 -r 500
```

---

## 🔥 Why Use This?
🔹 **AI Experimentation at Scale** – Handles massive AI workloads with dynamic resource allocation.  
🔹 **Optimized for LLM Training & Fine-Tuning** – Track multiple training runs efficiently.  
🔹 **Zero Waste, Cost-Efficient** – Scale MLflow servers only when needed, reducing costs.  
🔹 **Persistent Tracking Across Sessions** – Never lose experiment logs, models, or metadata.  
🔹 **Multi-Cloud Flexibility** – Adaptable to AWS, GCP, Azure, or on-prem Kubernetes.  

---

## 📚 Additional Resources
- **📖 Installation Steps:** [`tutorial/install_steps.txt`](tutorial/install_steps.txt)
- **🚀 Deployment Steps:** [`tutorial/deploy_steps.txt`](tutorial/deploy_steps.txt)
- **📜 AWS EFS Configuration:** [`src/installs/efs/efs-pv-pvc.yaml`](src/installs/efs/efs-pv-pvc.yaml)
- **📦 MLflow Knative Deployment:** [`src/deploy/mlflow-apefs-0001.yaml`](src/deploy/mlflow-apefs-0001.yaml)
- **📊 Load Testing with Locust:** [`src/test/111-locustfile.py`](src/test/111-locustfile.py)


