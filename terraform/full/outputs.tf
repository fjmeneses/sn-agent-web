output "azure_ai_services_resource_id" {
  description = "Existing Azure AI Services resource ID used for Entra-authenticated Speech synthesis"
  value       = data.azurerm_cognitive_account.ai_services.id
}

output "azure_speech_region" {
  description = "Existing Azure AI Services region used for Speech"
  value       = data.azurerm_cognitive_account.ai_services.location
}

output "azure_speech_endpoint" {
  description = "Existing Azure AI Services endpoint used for Speech"
  value       = data.azurerm_cognitive_account.ai_services.endpoint
}

output "azure_openai_endpoint" {
  description = "Existing Azure AI Services endpoint URL"
  value       = data.azurerm_cognitive_account.ai_services.endpoint
}

output "azure_openai_deployment" {
  description = "Existing Azure OpenAI deployment name"
  value       = var.openai_deployment_name
}

output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.acr.login_server
}

output "app_service_url" {
  description = "App Service default hostname"
  value       = "https://${azurerm_linux_web_app.app.default_hostname}"
}

output "resource_group_name" {
  description = "Resource group containing the deployed App Service and ACR"
  value       = azurerm_resource_group.main.name
}

