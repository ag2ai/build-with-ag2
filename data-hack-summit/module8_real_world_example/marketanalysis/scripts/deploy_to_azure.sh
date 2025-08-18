#!/bin/bash

# Script to deploy to Azure Container Apps using Azure CLI

# Variables
export RESOURCE_GROUP="marketanalysis-rg"
export CONTAINER_APP_NAME="marketanalysis"
export LOCATION="westeurope"
export ACR_NAME="marketanalysis-acr"
export VNET_NAME="marketanalysis-vnet"


echo -e "\033[0;32mChecking if already logged into Azure\033[0m"
if ! az account show > /dev/null 2>&1; then
    echo -e "\033[0;32mLogging into Azure\033[0m"
    az login
else
    echo -e "\033[0;32mAlready logged into Azure\033[0m"
fi

echo -e "\033[0;32mCreating resource group if it doesn't exists already\033[0m"
az group create --name $RESOURCE_GROUP --location $LOCATION

echo -e "\033[0;32mCreating azure container registry if it doesn't exists already\033[0m"
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true
rm ~/.docker/config.json
az acr login --name $ACR_NAME

echo -e "\033[0;32mBuilding and pushing docker image to azure container registry\033[0m"
docker build -t $ACR_NAME.azurecr.io/${CONTAINER_APP_NAME}:latest -f docker/Dockerfile .
docker push $ACR_NAME.azurecr.io/${CONTAINER_APP_NAME}:latest

echo -e "\033[0;32mChecking if container app environment exists\033[0m"
if ! az containerapp env show --name "$CONTAINER_APP_NAME-env" --resource-group $RESOURCE_GROUP > /dev/null 2>&1; then

    echo -e "\033[0;32mCreating vnet for container app environment\033[0m"
    az network vnet create --resource-group $RESOURCE_GROUP \
      --name $VNET_NAME --location $LOCATION --address-prefix 10.0.0.0/16
    az network vnet subnet create --resource-group $RESOURCE_GROUP \
      --vnet-name $VNET_NAME --name infrastructure-subnet \
      --address-prefixes 10.0.0.0/21
    az network vnet subnet update --resource-group $RESOURCE_GROUP \
      --vnet-name $VNET_NAME --name infrastructure-subnet \
      --delegations Microsoft.App/environments

    INFRASTRUCTURE_SUBNET=`az network vnet subnet show --resource-group ${RESOURCE_GROUP} --vnet-name $VNET_NAME --name infrastructure-subnet --query "id" -o tsv | tr -d '[:space:]'`

    echo -e "\033[0;32mCreating container app environment\033[0m"
    az containerapp env create \
      --name "$CONTAINER_APP_NAME-env" \
      --resource-group $RESOURCE_GROUP \
      --location $LOCATION \
      --infrastructure-subnet-resource-id $INFRASTRUCTURE_SUBNET
else
    echo -e "\033[0;32mContainer app environment already exists\033[0m"
fi

# echo -e "\033[0;32mUpdating azure.yml file\033[0m"
# export SUBSCRIPTION_ID=$(az account show --query id --output tsv)
# envsubst < azure.yml > azure.yml.tmp && mv azure.yml.tmp azure.yml

echo -e "\033[0;32mCreating container app\033[0m"
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment "$CONTAINER_APP_NAME-env" \
  --image $ACR_NAME.azurecr.io/${CONTAINER_APP_NAME}:latest \
  --target-port 8888 \
  --ingress 'external' \
  --query properties.configuration.ingress.fqdn \
  --registry-server $ACR_NAME.azurecr.io \
  --cpu 1 \
  --memory 2Gi \
  --min-replicas 0 \
  --max-replicas 2 \
  --env-vars OPENAI_API_KEY=$OPENAI_API_KEY

echo -e "\033[0;32mUpdating container app to expose all the service ports\033[0m"
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --yaml azure.yml

echo -e "\033[0;32mSetting up session affinity\033[0m"
az containerapp ingress sticky-sessions set \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --affinity sticky

echo -e "\033[0;32mFetching your Azure Container App's hosted URL\033[0m"
FQDN=$(az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)
echo -e "\033[0;32mYour Azure Container App's hosted URL is: https://$FQDN\033[0m"
