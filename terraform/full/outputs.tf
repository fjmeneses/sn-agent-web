output "azure_speech_key" {
  description = "Azure Speech Services primary key"
  value       = azurerm_cognitive_account.speech.primary_access_key
  sensitive   = true
}

output "azure_speech_region" {
  description = "Azure Speech Services region"
  value       = azurerm_resource_group.main.location
}

output "azure_openai_key" {
  description = "Azure OpenAI primary key"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint URL"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "azure_openai_deployment" {
  description = "Azure OpenAI deployment name"
  value       = azurerm_cognitive_deployment.model.name
}

output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  description = "ACR admin username"
  value       = azurerm_container_registry.acr.admin_username
  sensitive   = true
}

output "acr_admin_password" {
  description = "ACR admin password"
  value       = azurerm_container_registry.acr.admin_password
  sensitive   = true
}

output "app_service_url" {
  description = "App Service default hostname"
  value       = "https://${azurerm_linux_web_app.app.default_hostname}"
}
