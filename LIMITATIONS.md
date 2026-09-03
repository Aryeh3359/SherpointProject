# Architectural Seams & Cloud Constraints

## 1. M365 SharePoint Mocking
* **Constraint:** Microsoft 365 SharePoint lacks a persistent free-tier developer plan without paid tenant licensing.
* **Resolution:** In accordance with project instructions ("if something has no free tier, mock it behind an interface and document the seam"), the SharePoint Document Library was mocked using **Azure Blob Storage**. The ingestion pipeline binds to storage events via blob triggers, presenting an identical interface contract for document upload, deletion, and incremental indexing.

## 2. Infrastructure as Code & Quota Boundaries
* **Constraint:** Azure subscription quota limitations on Linux dynamic serverless compute (`SubscriptionIsOverQuotaForSku: Current Limit (Y1 VMs): 0`) prevent provisioning live Consumption App Service Plans in public regions without manual quota raise requests.
* **Resolution:** All infrastructure is fully specified via **Azure Bicep** (`infra/main.bicep`) defining:
  - Azure Storage Account & Document Container
  - Azure AI Search (Basic Tier)
  - Linux Function App & App Service Plan
* **CI/CD Automation:** The GitHub Actions pipeline (`.github/workflows/deploy.yml`) validates the Bicep template through `az deployment group validate`, ensuring the infrastructure is syntactically correct and fully deployable upon quota allocation.