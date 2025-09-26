# PowerShell script to check APIM configuration
# This script checks the named values and API operations in APIM

$subscriptionId = "1c47c29b-10d8-4bc6-a024-05ec921662cb"
$resourceGroupName = "rg-apim-mcp-app-2"
$apimServiceName = "apim-hvsvkzkl6s2ra"

Write-Host "🔍 Checking APIM Configuration..." -ForegroundColor Cyan
Write-Host "Subscription: $subscriptionId"
Write-Host "Resource Group: $resourceGroupName"
Write-Host "APIM Service: $apimServiceName"
Write-Host ""

# Check if user is logged in to Azure
try {
    $context = az account show --query "id" --output tsv 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Not logged in to Azure. Please run 'az login' first." -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Authenticated to Azure" -ForegroundColor Green
}
catch {
    Write-Host "❌ Azure CLI not available or not working properly" -ForegroundColor Red
    Write-Host "Please install/fix Azure CLI or use Azure Portal to check these manually:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual checks needed in Azure Portal:" -ForegroundColor Yellow
    Write-Host "1. Go to API Management service: $apimServiceName"
    Write-Host "2. Check Named Values for: EncryptionKey, EncryptionIV, EntraIDClientId, etc."
    Write-Host "3. Check APIs section for 'oauth' API"
    Write-Host "4. Check Operations under oauth API"
    Write-Host ""
    exit 1
}

Write-Host "🔑 Checking Named Values..." -ForegroundColor Yellow

# List of expected named values
$expectedNamedValues = @(
    "EncryptionKey",
    "EncryptionIV", 
    "EntraIDClientId",
    "EntraIDFicClientId",
    "EntraIDTenantId",
    "OAuthCallbackUri",
    "OAuthScopes",
    "McpClientId",
    "APIMGatewayURL",
    "MCPServer"
)

foreach ($namedValue in $expectedNamedValues) {
    try {
        $result = az apim nv show --service-name $apimServiceName --resource-group $resourceGroupName --named-value-id $namedValue --query "displayName" --output tsv 2>$null
        if ($LASTEXITCODE -eq 0 -and $result) {
            Write-Host "  ✅ $namedValue" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $namedValue (missing)" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "  ❌ $namedValue (error checking)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "🌐 Checking OAuth API Operations..." -ForegroundColor Yellow

# Check if oauth API exists
try {
    $apiResult = az apim api show --service-name $apimServiceName --resource-group $resourceGroupName --api-id "oauth" --query "displayName" --output tsv 2>$null
    if ($LASTEXITCODE -eq 0 -and $apiResult) {
        Write-Host "  ✅ OAuth API exists" -ForegroundColor Green
        
        # Check operations
        $expectedOperations = @(
            "register",
            "authorize", 
            "token",
            "oauth-callback",
            "register-options",
            "oauthmetadata-get",
            "oauthmetadata-options"
        )
        
        foreach ($operation in $expectedOperations) {
            try {
                $opResult = az apim api operation show --service-name $apimServiceName --resource-group $resourceGroupName --api-id "oauth" --operation-id $operation --query "displayName" --output tsv 2>$null
                if ($LASTEXITCODE -eq 0 -and $opResult) {
                    Write-Host "    ✅ $operation" -ForegroundColor Green
                } else {
                    Write-Host "    ❌ $operation (missing)" -ForegroundColor Red
                }
            }
            catch {
                Write-Host "    ❌ $operation (error checking)" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  ❌ OAuth API does not exist" -ForegroundColor Red
    }
}
catch {
    Write-Host "  ❌ Error checking OAuth API" -ForegroundColor Red
}

Write-Host ""
Write-Host "🔧 Next Steps:" -ForegroundColor Cyan
Write-Host "1. If named values are missing, they need to be created in APIM"
Write-Host "2. If OAuth API operations are missing, redeploy the infrastructure"
Write-Host "3. Check Azure portal APIM logs for detailed error information"
Write-Host "4. Verify Entra ID app registration is complete"