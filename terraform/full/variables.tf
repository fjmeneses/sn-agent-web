variable "subscription_id" {
  description = "Azure subscription ID used for provisioning"
  type        = string
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "southeastasia"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "voice-ai-agent-rg"
}

variable "prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "voiceai"

  validation {
    condition     = can(regex("^[a-z0-9]{3,14}$", var.prefix))
    error_message = "The prefix must be 3-14 lowercase letters or numbers so generated Azure resource names remain valid."
  }
}

variable "ai_services_account_name" {
  description = "Existing Azure AI Foundry / Azure AI Services account name"
  type        = string
}

variable "ai_services_resource_group_name" {
  description = "Resource group containing the existing Azure AI Foundry / Azure AI Services account"
  type        = string
}

variable "openai_deployment_name" {
  description = "Existing model deployment name in the Azure AI Services account"
  type        = string
}

variable "tts_voice" {
  description = "Azure TTS voice name"
  type        = string
  default     = "en-US-AndrewNeural"
}

variable "unattended" {
  description = "Unattended mode flag"
  type        = string
  default     = "false"
}

variable "app_sku" {
  description = "App Service Plan SKU"
  type        = string
  default     = "B2"
}
