#!/bin/bash

# Set your GCP project ID
PROJECT_ID="your-project-id"
REGION="us-central1"
IMAGE_NAME="ag2-agent"
REPOSITORY="ag2-agent-repo2"  # Artifact Registry repo name

# Set the project
gcloud config set project ${PROJECT_ID}

# Build and push the image to Artifact Registry
echo "Building Docker image..."
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest

# Deploy to Cloud Run (Recommended for web APIs)
echo "Deploying to Cloud Run..."
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

echo "Deployment complete!"
echo "Get your service URL:"
gcloud run services describe ${IMAGE_NAME} --region=${REGION} --format="value(status.url)"
