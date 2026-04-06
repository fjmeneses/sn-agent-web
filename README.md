# Voice AI Agent

Browser-based voice AI agent using Azure Speech and OpenAI.

## Prerequisites

- **Docker** (for running locally)
- **Terraform** (for deploying Azure services)
- **Chrome browser** (for frontend)

## Setup

### 1. Deploy Azure Services

Navigate to terraform directory and deploy:

**Core Mode** (minimal cost, run app locally):
```bash
cd terraform/core
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform init
terraform apply
```

**Full Mode** (includes Azure Container Registry + App Service):
```bash
cd terraform/full
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform init
terraform apply
```

Terraform will output the required credentials.

### 2. Configure Environment

```bash
# In project root
./setup-env.sh
```

Follow the prompts to configure Azure credentials.

### 3. Run Application

**Core Mode (local):**
```bash
# Start backend
docker compose up -d

# Start frontend
python3 serve.py

# Open http://localhost:3000
```

**Full Mode (Azure):**
Application is deployed to Azure App Service. Access via the URL from Terraform outputs.

## Usage

1. Allow microphone permission
2. Speak into microphone
3. View transcript and agent response
4. Press ENTER to hear response

---

For detailed architecture and API documentation, see [QUICKSTART.md](QUICKSTART.md)

## License

MIT

## Credits

Based on the [azure-sn-agent](https://github.com/egubi/azure-sn-agent) CLI reference implementation.
