#!/usr/bin/env bash
set -e

# ==============================================================================
# Setup Environment Script
# ==============================================================================
# Automatically configures .env file from Terraform outputs
# 
# Usage:
#   ./setup-env.sh              ← uses terraform/core/ (AI services only)
#   ./setup-env.sh --mode full  ← uses terraform/full/ (full cloud deployment)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# Parse command line arguments
MODE="core"
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --mode) MODE="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Validate mode
if [[ "$MODE" != "core" && "$MODE" != "full" ]]; then
    echo "Error: Unknown mode '$MODE'. Use 'core' or 'full'."
    exit 1
fi

TERRAFORM_DIR="$SCRIPT_DIR/terraform/$MODE"

# Check if Terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "Error: Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

echo "========================================"
echo "SecondNatureAgent Agent - Environment Setup"
echo "========================================"
echo "Mode: $MODE"
echo "Terraform dir: $TERRAFORM_DIR"
echo ""

# Change to Terraform directory
cd "$TERRAFORM_DIR"

# Check if Terraform is initialized
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
    echo ""
fi

# Check if Terraform state exists
if [ ! -f "terraform.tfstate" ]; then
    echo "Error: No Terraform state found. Please run 'terraform apply' first."
    echo ""
    echo "Steps:"
    echo "  1. cd $TERRAFORM_DIR"
    echo "  2. cp terraform.tfvars.example terraform.tfvars"
    echo "  3. Edit terraform.tfvars with your configuration"
    echo "  4. terraform apply"
    echo "  5. Run this script again"
    exit 1
fi

echo "Extracting Terraform outputs..."
echo ""

# Extract outputs
AI_SERVICES_RESOURCE_ID=$(terraform output -raw azure_ai_services_resource_id 2>/dev/null || echo "")
SPEECH_ENDPOINT=$(terraform output -raw azure_speech_endpoint 2>/dev/null || echo "")
SPEECH_REGION=$(terraform output -raw azure_speech_region 2>/dev/null || echo "")
OPENAI_ENDPOINT=$(terraform output -raw azure_openai_endpoint 2>/dev/null || echo "")
OPENAI_DEPLOYMENT=$(terraform output -raw azure_openai_deployment 2>/dev/null || echo "")

# Validate core outputs
if [[ -z "$AI_SERVICES_RESOURCE_ID" || -z "$SPEECH_ENDPOINT" || -z "$OPENAI_ENDPOINT" ]]; then
    echo "Error: Failed to retrieve Terraform outputs. Please check your Terraform state."
    exit 1
fi

# Return to project root
cd "$SCRIPT_DIR"

echo "Writing to $ENV_FILE..."
echo ""

# Write .env file
cat > "$ENV_FILE" << EOF
# SecondNatureAgent Agent Backend - Environment Configuration
# Auto-generated from Terraform outputs (mode: $MODE)
# Generated on: $(date)

# ==============================================================================
# Azure AI Services / Speech Configuration
# ==============================================================================
AZURE_AI_SERVICES_RESOURCE_ID=$AI_SERVICES_RESOURCE_ID
AZURE_SPEECH_ENDPOINT=$SPEECH_ENDPOINT
AZURE_SPEECH_REGION=$SPEECH_REGION

# ==============================================================================
# Azure OpenAI Configuration
# ==============================================================================
AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT=$OPENAI_DEPLOYMENT
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# ==============================================================================
# Azure Text-to-Speech Configuration
# ==============================================================================
AZURE_TTS_VOICE=en-US-AndrewNeural

# ==============================================================================
# Agent Mode Configuration
# ==============================================================================
UNATTENDED=false
EOF

echo "✓ Environment file created successfully!"
echo ""

# Mode-specific outputs
if [ "$MODE" == "full" ]; then
    echo "========================================"
    echo "Full Mode - Additional Information"
    echo "========================================"
    echo ""
    
    cd "$TERRAFORM_DIR"
    
    ACR_SERVER=$(terraform output -raw acr_login_server 2>/dev/null || echo "")
    APP_URL=$(terraform output -raw app_service_url 2>/dev/null || echo "")
    
    if [[ -n "$ACR_SERVER" ]]; then
        echo "ACR Login Server : $ACR_SERVER"
        echo "App Service URL  : $APP_URL"
        echo ""
        echo "Next steps — Push your Docker image to ACR:"
        echo ""
        echo "  1. Login to ACR:"
        echo "     az acr login --name ${ACR_SERVER%%.*}"
        echo ""
        echo "  2. Build and tag your image:"
        echo "     docker build -t voice-ai-agent:latest ."
        echo "     docker tag voice-ai-agent:latest $ACR_SERVER/voice-ai-agent:latest"
        echo ""
        echo "  3. Push to ACR:"
        echo "     docker push $ACR_SERVER/voice-ai-agent:latest"
        echo ""
        echo "  4. Restart the App Service to pull the new image:"
        echo "     az webapp restart --name <app-name> --resource-group <rg-name>"
        echo ""
    fi
    
    cd "$SCRIPT_DIR"
fi

echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "You can now run your application locally:"
echo "  docker-compose up"
echo ""
