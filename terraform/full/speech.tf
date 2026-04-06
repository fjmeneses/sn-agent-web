# Azure Speech Services (STT + TTS)
resource "azurerm_cognitive_account" "speech" {
  name                = "${var.prefix}-speech-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  kind                = "SpeechServices"
  sku_name            = "S0"

  tags = {
    Environment = "Development"
    Service     = "Speech"
  }
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}
