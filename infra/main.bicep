param location string = resourceGroup().location
param appName string = 'ragagent${uniqueString(resourceGroup().id)}'

// Storage Account for the Blob Library and Queue
resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  // Ensure the name is strictly alphanumeric and under 24 characters safely
  name: toLower(take(replace(appName, '-', ''), 24))
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2022-09-01' = {
  parent: storageAccount
  name: 'default'
}

// This acts as your mocked SharePoint library
resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2022-09-01' = {
  parent: blobService
  name: 'documents'
  properties: {
    publicAccess: 'None'
  }
}

// Azure AI Search (Basic Tier)
resource searchService 'Microsoft.Search/searchServices@2022-09-01' = {
  name: '${appName}-search'
  location: location
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
  }
}

// App Service Plan (Consumption - Serverless)
resource hostingPlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${appName}-plan'
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true 
  }
}

// Function App (Python Backend)
resource functionApp 'Microsoft.Web/sites@2022-03-01' = {
  name: 'ragagent-func'
  location: location
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: hostingPlan.id
    siteConfig: {
      linuxFxVersion: 'python|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
      ]
    }
  }
}
