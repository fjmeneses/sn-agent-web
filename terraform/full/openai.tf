# Existing Azure AI Foundry / Azure AI Services account.
data "azurerm_cognitive_account" "ai_services" {
  name                = var.ai_services_account_name
  resource_group_name = var.ai_services_resource_group_name
}
