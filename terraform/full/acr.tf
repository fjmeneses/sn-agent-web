# Azure Container Registry
resource "azurerm_container_registry" "acr" {
  name                = "${var.prefix}acr${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false

  tags = {
    Environment = "Development"
    Service     = "ContainerRegistry"
  }
}

resource "azurerm_role_assignment" "app_acr_pull" {
  scope                            = azurerm_container_registry.acr.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_linux_web_app.app.identity[0].principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "app_ai_services_user" {
  scope                            = data.azurerm_cognitive_account.ai_services.id
  role_definition_name             = "Cognitive Services User"
  principal_id                     = azurerm_linux_web_app.app.identity[0].principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "app_openai_user" {
  scope                            = data.azurerm_cognitive_account.ai_services.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = azurerm_linux_web_app.app.identity[0].principal_id
  skip_service_principal_aad_check = true
}
