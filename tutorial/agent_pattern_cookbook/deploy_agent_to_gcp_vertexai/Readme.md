# AutoGen AG2 Agent - GCP Cloud Run Deployment

This project deploys an AutoGen AG2 (AutoGen 2.0) conversational agent to Google Cloud Platform (GCP) using Cloud Run. The agent is built with FastAPI to provide a REST API interface for chat interactions using Google's Gemini model.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Project Setup](#project-setup)
- [Local Development](#local-development)
- [GCP Setup](#gcp-setup)
- [Deployment](#deployment)
- [API Usage](#api-usage)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

## 🎯 Overview

This project demonstrates how to:
- Build an AutoGen AG2 conversational agent using Gemini API
- Containerize the agent with Docker
- Deploy to GCP Cloud Run as a scalable web service
- Expose the agent via REST API endpoints


## 📦 Prerequisites

Before you begin, ensure you have:

1. **Google Cloud Platform Account**
   - Active GCP account with billing enabled
   - Access to create projects and enable APIs

2. **Google Cloud SDK (gcloud CLI)**

   # Install gcloud CLI
   # macOS:
   brew install google-cloud-sdk

   # Or download from:
   # https://cloud.google.com/sdk/docs/install
   3. **Docker** (optional, for local testing)sh
   # Install Docker Desktop
   # https://www.docker.com/products/docker-desktop
   4. **Python 3.13+**
   python --version  # Should be 3.13 or higher
   5. **Gemini API Key**
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🚀 Project Setup

### 1. Clone or Navigate to Project Directory

cd deply-ag2-to-gcp-vertexai

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate### 3. Install Dependencies

pip install -r requirements.txt### 4. Set Up Environment Variables
```

Create a `.env` file in the project root:

GEMINI_API_KEY=your_gemini_api_key_here**⚠️ Important:** Never commit `.env` file to version control. It's already in `.gitignore`.

## 💻 Local Development

### Run the Agent Locally
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Set environment variable
export GEMINI_API_KEY=your_gemini_api_key

# Run the FastAPI server
python agent.pyThe server will start on `http://localhost:8080`

### Test the API

**Health Check:**
curl http://localhost:8080/**Chat Endpoint:**
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "A joke about NYC.", "max_turn": 1}'### Test with Docker Locally (Optional)
h
# Build the image
docker build -t ag2-agent:local .

# Run the container
docker run -p 8080:8080 -e GEMINI_API_KEY=your_key_here ag2-agent:local## ☁️ GCP Setup
```
### Step 1: Create a New GCP Project

**Via Console:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top
3. Click "New Project"
4. Enter project name (e.g., "ag2-agent-project")
5. Click "Create"

**Via CLI:**sh
gcloud projects create YOUR_PROJECT_ID --name="AG2 Agent Project"### Step 2: Set the Active Project

gcloud config set project YOUR_PROJECT_ID### Step 3: Enable Required APIs
sh
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  containerregistry.googleapis.com**Via Console:**
1. Go to **APIs & Services** → **Library**
2. Search and enable each API:
   - Cloud Build API
   - Cloud Run API
   - Vertex AI API
   - Artifact Registry API
   - Container Registry API

### Step 4: Set Up Authentication

# Login to GCP
gcloud auth login

# Set up Application Default Credentials
gcloud auth application-default login

# Configure Docker authentication
gcloud auth configure-docker

### Step 5: Link Billing Account

1. Go to **Billing** in GCP Console
2. Link a billing account to your project
3. ⚠️ **Required** for Cloud Run and Vertex AI services

### Step 6: Create Artifact Registry Repository

PROJECT_ID="your-project-id"
REGION="us-central1"

gcloud artifacts repositories create ag2-agent-repo2 \
  --repository-format=docker \
  --location=${REGION} \
  --description="Docker repository for AG2 agent"**Via Console:**
1. Go to **Artifact Registry** → **Create Repository**
2. Name: `ag2-agent-repo2`
3. Format: Docker
4. Location: `us-central1` (or your preferred region)

## 🚢 Deployment

### Option 1: Using deploy.sh Script (Recommended)

1. **Update deploy.sh with your project details:**

   Edit `deploy.sh` and update:
   PROJECT_ID="your-actual-project-id"
   REPOSITORY="ag2-agent-repo2"  # Match your Artifact Registry repo name
   2. **Set your Gemini API key:**
   export GEMINI_API_KEY=your_gemini_api_key_here
   3. **Make script executable and run:**
   chmod +x deploy.sh
   ./deploy.sh
      The script will:
   - Build the Docker image
   - Push to Artifact Registry
   - Deploy to Cloud Run
   - Display the service URL

### Option 2: Using Cloud Build

1. **Update cloudbuild.yaml substitutions:**

   Edit `cloudbuild.yaml`:
   substitutions:
     _REGION: 'us-central1'
     _REPOSITORY: 'ag2-agent-repo2'  # Match your repo name
     _IMAGE_NAME: 'ag2-agent'
   2. **Submit the build:**
   gcloud builds submit --config cloudbuild.yaml
   3. **Deploy to Cloud Run:**

   gcloud run deploy ag2-agent \
     --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ag2-agent-repo2/ag2-agent:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars GEMINI_API_KEY=your_gemini_api_key \
     --memory 2Gi \
     --cpu 2 \
     --timeout 3600 \
     --port 8080
   ### Option 3: Manual Step-by-Step Deployment

# 1. Set project
PROJECT_ID="your-project-id"
REGION="us-central1"
REPOSITORY="ag2-agent-repo2"
IMAGE_NAME="ag2-agent"

gcloud config set project ${PROJECT_ID}

# 2. Build and push image
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest

# 3. Deploy to Cloud Run
gcloud run deploy ${IMAGE_NAME} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=${GEMINI_API_KEY} \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --port 8080

# 4. Get service URL
gcloud run services describe ${IMAGE_NAME} --region=${REGION} --format="value(status.url)"## 📡 API Usage

Once deployed, your service will have a public URL. Use it as follows:

### Health Check

curl https://your-service-url.run.app/**Response:**
{"status": "healthy"}### Chat Endpoint

curl -X POST https://your-service-url.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "A joke about NYC.",
    "max_turn": 1
  }'**Response:**
{
  "response": "Agent response here..."
}### Using Python
hon
import requests

url = "https://your-service-url.run.app/chat"
payload = {
    "message": "A joke about NYC.",
    "max_turn": 1
}

response = requests.post(url, json=payload)
print(response.json())
## 🔧 Troubleshooting

### Issue: Container failed to start and listen on port 8080

**Cause:** The application must listen on the port specified by the `PORT` environment variable (default 8080).

**Solution:** Ensure `agent.py` uses:
port = int(os.getenv("PORT", 8080))
uvicorn.run(app, host="0.0.0.0", port=port)

### Issue: Quota exceeded for Vertex AI

**Cause:** New GCP projects have limited quotas for Vertex AI resources.

**Solution:**
- Use Cloud Run instead (different quota pool)
- Request quota increase in GCP Console → IAM & Admin → Quotas

### Issue: Authentication errors

**Solution:**
gcloud auth login
gcloud auth application-default login
gcloud auth configure-docker### Issue: API not enabled

**Solution:**
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

### Issue: Build fails with dependency errors

**Solution:**
- Check `requirements.txt` has all dependencies
- Ensure Python version in Dockerfile matches your local version
- Try building locally first: `docker build -t test .`

### View Logs

# Cloud Run logs
gcloud run services logs read ag2-agent --region=us-central1

# Cloud Build logs
gcloud builds list
gcloud builds log BUILD_ID## 📁 Project Structure
