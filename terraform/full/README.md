# Full Mode Deployment Guide

This Terraform configuration deploys the complete SecondNatureAgent Agent infrastructure to Azure, including:

- **Azure AI Services** (Speech Services + OpenAI)
- **Azure Container Registry (ACR)** for Docker image storage
- **Azure App Service** (Linux container) with WebSockets enabled

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Terraform >= 1.3.0 installed
- Docker installed for building and pushing images

## Deployment Steps

### 1. Configure Variables

Copy the example variables file and customize as needed:

```bash
cd terraform/full
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your preferred values.

### 2. Initialize and Apply Terraform

```bash
terraform init
terraform plan
terraform apply
```

This will provision all Azure resources including the App Service configured to pull from ACR.

### 3. Build and Push Docker Image

After Terraform completes, get your ACR login server:

```bash
ACR_SERVER=$(terraform output -raw acr_login_server)
```

Login to ACR with your Azure identity:

```bash
az acr login --name ${ACR_SERVER%%.azurecr.io}
```

Build and push your Docker image from the project root:

```bash
cd ../..  # Return to project root
docker build -t voice-ai-agent:latest .
docker tag voice-ai-agent:latest $ACR_SERVER/voice-ai-agent:latest
docker push $ACR_SERVER/voice-ai-agent:latest
```

### 4. Restart App Service

After pushing the image, restart the App Service to pull the latest image:

```bash
cd terraform/full
APP_NAME=$(az webapp list --resource-group $(terraform output -raw resource_group_name) --query "[0].name" -o tsv)
az webapp restart --name $APP_NAME --resource-group $(terraform output -raw resource_group_name)
```

### 5. Access Your Application

Your application will be available at:

```bash
terraform output app_service_url
```

## Configuration

All environment variables are automatically configured as App Service App Settings:

- `AZURE_AI_SERVICES_RESOURCE_ID` - Existing Azure AI Services resource ID
- `AZURE_SPEECH_ENDPOINT` - Existing Azure AI Services endpoint for Speech
- `AZURE_SPEECH_REGION` - Azure AI Services region
- `AZURE_OPENAI_ENDPOINT` - Azure AI Services endpoint URL
- `AZURE_OPENAI_DEPLOYMENT` - Model deployment name
- `AZURE_OPENAI_API_VERSION` - Azure OpenAI API version
- `AZURE_TTS_VOICE` - TTS voice configuration
- `UNATTENDED` - Agent mode flag
- `WEBSITES_PORT` - Container port (8000)

**No .env file is needed** — all configuration is managed through Terraform. The App Service uses a system-assigned managed identity to call Azure AI Services and pull images from ACR.

## Monitoring

- View logs: `az webapp log tail --name $APP_NAME --resource-group <rg-name>`
- Check App Service in Azure Portal for deployment status and logs

## Clean Up

To destroy all resources:

```bash
terraform destroy
```

## Troubleshooting

**Container not starting?**
- Check App Service logs for errors
- Verify the Docker image was pushed successfully to ACR
- Ensure the image tag matches what App Service is configured to pull

**WebSocket connection issues?**
- WebSockets are enabled by default in this configuration
- Check firewall/network rules if accessing from corporate network

**ACR authentication failures?**
- Admin access is disabled by default
- App Service pulls images with managed identity and the `AcrPull` role
