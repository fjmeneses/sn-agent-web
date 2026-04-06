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
}

variable "openai_deployment_name" {
  description = "Name for the OpenAI model deployment"
  type        = string
  default     = "gpt-4o-mini"
}

variable "openai_model_name" {
  description = "OpenAI model name"
  type        = string
  default     = "gpt-4o-mini"
}

variable "openai_model_version" {
  description = "OpenAI model version"
  type        = string
  default     = "2024-07-18"
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
