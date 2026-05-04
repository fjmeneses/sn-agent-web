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
  https_only          = true

  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = true
    container_registry_use_managed_identity = true
    use_32_bit_worker                       = false

    application_stack {
      docker_image_name   = "voice-ai-agent:latest"
      docker_registry_url = "https://${azurerm_container_registry.acr.login_server}"
    }

    # Enable WebSockets
    websockets_enabled = true
  }

  app_settings = {
    # Docker configuration
    "WEBSITES_PORT"    = "8000"
    "DOCKER_ENABLE_CI" = "true"

    # Azure AI Services / Speech configuration. Authentication uses the App Service managed identity.
    "AZURE_AI_SERVICES_RESOURCE_ID" = data.azurerm_cognitive_account.ai_services.id
    "AZURE_SPEECH_ENDPOINT"         = data.azurerm_cognitive_account.ai_services.endpoint
    "AZURE_SPEECH_REGION"           = data.azurerm_cognitive_account.ai_services.location

    # Azure OpenAI configuration. Authentication uses the App Service managed identity.
    "AZURE_OPENAI_ENDPOINT"    = data.azurerm_cognitive_account.ai_services.endpoint
    "AZURE_OPENAI_DEPLOYMENT"  = var.openai_deployment_name
    "AZURE_OPENAI_API_VERSION" = "2024-12-01-preview"

    # TTS Configuration
    "AZURE_TTS_VOICE" = var.tts_voice

    # Agent Mode
    "UNATTENDED" = var.unattended
  }

  tags = {
    Environment = "Development"
    Service     = "AppService"
  }
}
