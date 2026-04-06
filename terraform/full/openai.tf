# Azure OpenAI Service
resource "azurerm_cognitive_account" "openai" {
  name                = "${var.prefix}-openai-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  kind                = "OpenAI"
  sku_name            = "S0"

  tags = {
    Environment = "Development"
    Service     = "OpenAI"
  }
}

# OpenAI Model Deployment
resource "azurerm_cognitive_deployment" "model" {
  name                 = var.openai_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.openai_model_name
    version = var.openai_model_version
  }

  scale {
    type = "Standard"
  }
}
