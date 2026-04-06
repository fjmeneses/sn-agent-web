# App Service Plan (Linux, B2)
resource "azurerm_service_plan" "plan" {
  name                = "${var.prefix}-plan-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.app_sku

  tags = {
    Environment = "Development"
    Service     = "AppServicePlan"
  }
}

# App Service Web App (Linux container)
resource "azurerm_linux_web_app" "app" {
  name                = "${var.prefix}-app-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.plan.id

  site_config {
    always_on = true

    application_stack {
      docker_image_name   = "voice-ai-agent:latest"
      docker_registry_url = "https://${azurerm_container_registry.acr.login_server}"
    }

    # Enable WebSockets
    websockets_enabled = true
  }

  app_settings = {
    # Docker configuration
    "WEBSITES_PORT"                        = "8000"
    "DOCKER_REGISTRY_SERVER_URL"           = "https://${azurerm_container_registry.acr.login_server}"
    "DOCKER_REGISTRY_SERVER_USERNAME"      = azurerm_container_registry.acr.admin_username
    "DOCKER_REGISTRY_SERVER_PASSWORD"      = azurerm_container_registry.acr.admin_password
    "DOCKER_ENABLE_CI"                     = "true"
    
    # Azure Speech Services
    "AZURE_SPEECH_KEY"                     = azurerm_cognitive_account.speech.primary_access_key
    "AZURE_SPEECH_REGION"                  = azurerm_resource_group.main.location
    
    # Azure OpenAI
    "AZURE_OPENAI_KEY"                     = azurerm_cognitive_account.openai.primary_access_key
    "AZURE_OPENAI_ENDPOINT"                = azurerm_cognitive_account.openai.endpoint
    "AZURE_OPENAI_DEPLOYMENT"              = azurerm_cognitive_deployment.model.name
    
    # TTS Configuration
    "AZURE_TTS_VOICE"                      = var.tts_voice
    
    # Agent Mode
    "UNATTENDED"                           = var.unattended
  }

  tags = {
    Environment = "Development"
    Service     = "AppService"
  }
}
