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
