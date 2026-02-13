@description('The name of the API Management service')
param apimServiceName string

@description('The name of the Function App hosting the Sentinel webhook endpoint')
param functionAppName string

// Get reference to the existing APIM service
resource apimService 'Microsoft.ApiManagement/service@2023-05-01-preview' existing = {
  name: apimServiceName
}

// Get reference to the Function App
resource functionApp 'Microsoft.Web/sites@2023-12-01' existing = {
  name: functionAppName
}

// Create a named value in APIM to store the function key
resource functionHostKeyNamedValue 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apimService
  name: 'sentinel-function-host-key'
  properties: {
    displayName: 'sentinel-function-host-key'
    secret: true
    value: listKeys('${functionApp.id}/host/default', functionApp.apiVersion).masterKey
  }
}

// Create the Sentinel API definition in APIM
resource sentinelApi 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = {
  parent: apimService
  name: 'sentinel-agent'
  properties: {
    displayName: 'Sentinel AI Agent API'
    description: 'AI Agent webhook endpoints for Microsoft Sentinel Playbooks'
    subscriptionRequired: false
    path: 'sentinel'
    protocols: [
      'https'
    ]
    serviceUrl: 'https://${functionApp.properties.defaultHostName}/api'
  }
  dependsOn: [
    functionHostKeyNamedValue
  ]
}

// Apply policy at the API level for authentication and CORS
resource sentinelApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2023-05-01-preview' = {
  parent: sentinelApi
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('sentinel-api.policy.xml')
  }
}

// Create the webhook endpoint operation
resource sentinelWebhookOperation 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = {
  parent: sentinelApi
  name: 'sentinel-webhook'
  properties: {
    displayName: 'Sentinel AI Agent Webhook'
    method: 'POST'
    urlTemplate: '/ai-agent/webhook'
    description: 'Webhook endpoint for processing Sentinel Playbook incidents and returning AI insights'
    request: {
      description: 'Sentinel incident data from playbook'
      representations: [
        {
          contentType: 'application/json'
        }
      ]
    }
    responses: [
      {
        statusCode: 200
        description: 'Successful processing with AI recommendations'
        representations: [
          {
            contentType: 'application/json'
          }
        ]
      }
      {
        statusCode: 400
        description: 'Invalid request payload'
      }
      {
        statusCode: 500
        description: 'Internal server error'
      }
    ]
  }
}

// Output the API ID for reference
output apiId string = sentinelApi.id
output webhookUrl string = '${apimService.properties.gatewayUrl}/sentinel/ai-agent/webhook'