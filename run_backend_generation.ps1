# ═════════════════════════════════════════════════════════════════════════
# FORGE Backend Generation - Complete Workflow
# ═════════════════════════════════════════════════════════════════════════
# This script runs all backend generation commands for ecom-elegance-main
# from start to finish, creating a complete production-ready backend.
# ═════════════════════════════════════════════════════════════════════════

param(
    [string]$ProjectPath = "C:\Users\SAGAR\Downloads\BACK4\ecom-elegance-main",
    [string]$Framework = "express",
    [string]$Database = "postgresql",
    [string]$Mode = "hybrid",
    [switch]$SkipAnalyze,
    [switch]$SkipGenerate,
    [switch]$SkipReview,
    [switch]$AutoFix,
    [switch]$DryRun
)

# Colors for output
function Write-Step {
    param([string]$Message)
    Write-Host "`n═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

# Banner
Write-Host @"

    ███████╗ ██████╗ ██████╗  ██████╗ ███████╗
    ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
    █████╗  ██║   ██║██████╔╝██║  ███╗█████╗  
    ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  
    ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
    ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
                                              
    Backend Generation - Complete Workflow
    
"@ -ForegroundColor Cyan

Write-Info "Project: $ProjectPath"
Write-Info "Framework: $Framework"
Write-Info "Database: $Database"
Write-Info "Mode: $Mode"

if ($DryRun) {
    Write-Host "`n⚠️  DRY RUN MODE - No files will be written" -ForegroundColor Yellow
}

# Check if project exists
if (-not (Test-Path $ProjectPath)) {
    Write-Error "Project path not found: $ProjectPath"
    Write-Host "Please ensure the ecom-elegance-main project exists at the specified location."
    exit 1
}

# Ensure we're in the FORGE directory
$forgeDir = $PSScriptRoot
Set-Location $forgeDir
Write-Info "Working from: $forgeDir"

# Activate virtual environment if it exists
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Info "Activating virtual environment..."
    & .\.venv\Scripts\Activate.ps1
    Write-Success "Virtual environment activated"
} else {
    Write-Host "⚠️  No virtual environment found. Make sure dependencies are installed." -ForegroundColor Yellow
}

# ═════════════════════════════════════════════════════════════════════════
# STEP 1: ANALYZE - Analyze frontend and infer backend architecture
# ═════════════════════════════════════════════════════════════════════════

if (-not $SkipAnalyze) {
    Write-Step "STEP 1: Analyzing Frontend Code"
    Write-Info "This will analyze the frontend to infer models, APIs, and relationships..."
    
    $analyzeCmd = "python main.py backend analyze `"$ProjectPath`" --reindex"
    Write-Host "`n> $analyzeCmd" -ForegroundColor DarkGray
    
    Invoke-Expression $analyzeCmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Frontend analysis complete!"
    } else {
        Write-Error "Analysis failed with exit code $LASTEXITCODE"
        Write-Host "`nTroubleshooting:" -ForegroundColor Yellow
        Write-Host "  - Ensure the project contains frontend code (React, Vue, etc.)"
        Write-Host "  - Check that all dependencies are installed"
        Write-Host "  - Verify .env configuration"
        
        $continue = Read-Host "`nContinue anyway? (y/N)"
        if ($continue -ne 'y' -and $continue -ne 'Y') {
            exit 1
        }
    }
    
    Write-Host "`nPress any key to continue to generation..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} else {
    Write-Host "`n⏭️  Skipping analyze step" -ForegroundColor Yellow
}

# ═════════════════════════════════════════════════════════════════════════
# STEP 2: GENERATE - Generate complete backend code
# ═════════════════════════════════════════════════════════════════════════

if (-not $SkipGenerate) {
    Write-Step "STEP 2: Generating Backend Code"
    Write-Info "This will generate complete backend code based on the analysis..."
    Write-Info "Mode: $Mode"
    
    if ($Mode -eq "multi") {
        Write-Host "`n🤖 Multi-Agent Mode (5-10 min):" -ForegroundColor Cyan
        Write-Host "  • Schema Designer - Database schema"
        Write-Host "  • API Architect - REST endpoints"
        Write-Host "  • Service Architect - Business logic"
        Write-Host "  • Auth Planner - Authentication/Authorization"
        Write-Host "  • Integration Manager - External services"
        Write-Host "  • And 3 more specialized agents..."
    } elseif ($Mode -eq "single") {
        Write-Host "`n⚡ Single-Agent Mode (1-2 min):" -ForegroundColor Cyan
        Write-Host "  • Fast prototyping"
        Write-Host "  • Good for MVPs"
    } else {
        Write-Host "`n🎯 Hybrid Mode:" -ForegroundColor Cyan
        Write-Host "  • Auto-selects based on project complexity"
    }
    
    $outputDir = Join-Path $ProjectPath "backend"
    $generateCmd = "python main.py backend generate `"$ProjectPath`" -o `"$outputDir`" -f $Framework -d $Database -m $Mode"
    
    if ($DryRun) {
        $generateCmd += " --dry-run"
    }
    
    Write-Host "`n> $generateCmd" -ForegroundColor DarkGray
    Write-Host "`n⏳ This may take several minutes..." -ForegroundColor Yellow
    
    Invoke-Expression $generateCmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Backend generation complete!"
        Write-Info "Backend code written to: $outputDir"
    } else {
        Write-Error "Generation failed with exit code $LASTEXITCODE"
        
        $continue = Read-Host "`nContinue to review step? (y/N)"
        if ($continue -ne 'y' -and $continue -ne 'Y') {
            exit 1
        }
    }
    
    Write-Host "`nPress any key to continue to review..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} else {
    Write-Host "`n⏭️  Skipping generate step" -ForegroundColor Yellow
}

# ═════════════════════════════════════════════════════════════════════════
# STEP 3: REVIEW - Code quality and security review
# ═════════════════════════════════════════════════════════════════════════

if (-not $SkipReview) {
    Write-Step "STEP 3: Reviewing Generated Code"
    Write-Info "Analyzing code quality, security, and best practices..."
    
    $backendPath = Join-Path $ProjectPath "backend"
    
    if (Test-Path $backendPath) {
        $reviewOutput = Join-Path $ProjectPath "backend_review_report.md"
        $reviewCmd = "python main.py backend review `"$backendPath`" -o `"$reviewOutput`" -v"
        
        Write-Host "`n> $reviewCmd" -ForegroundColor DarkGray
        
        Invoke-Expression $reviewCmd
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Code review complete!"
            Write-Info "Review report saved to: $reviewOutput"
            
            # Ask if user wants to view the report
            $viewReport = Read-Host "`nOpen review report? (y/N)"
            if ($viewReport -eq 'y' -or $viewReport -eq 'Y') {
                if (Get-Command code -ErrorAction SilentlyContinue) {
                    code $reviewOutput
                } else {
                    Start-Process notepad $reviewOutput
                }
            }
        } else {
            Write-Host "⚠️  Review completed with warnings" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️  Backend directory not found, skipping review" -ForegroundColor Yellow
    }
    
    Write-Host "`nPress any key to continue..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} else {
    Write-Host "`n⏭️  Skipping review step" -ForegroundColor Yellow
}

# ═════════════════════════════════════════════════════════════════════════
# STEP 4: OPTIONAL - Add custom models or endpoints
# ═════════════════════════════════════════════════════════════════════════

Write-Step "STEP 4: Additional Customizations (Optional)"
Write-Host @"

You can now add custom models or endpoints:

1. Add a model:
   python main.py backend add-model "$ProjectPath" <ModelName> -f '[{"name":"field1","type":"string"}]'

2. Add an endpoint:
   python main.py backend add-endpoint "$ProjectPath" GET /api/custom

3. Sync with frontend changes:
   python main.py backend sync "$ProjectPath"

4. Debug specific issues:
   python main.py backend debug "$backendPath" -e "error message"

5. Auto-fix code issues:
   python main.py backend fix "$backendPath" -f app.py

"@ -ForegroundColor Cyan

$customize = Read-Host "Would you like to add custom models/endpoints now? (y/N)"

if ($customize -eq 'y' -or $customize -eq 'Y') {
    Write-Host "`n1. Add Model"
    Write-Host "2. Add Endpoint"
    Write-Host "3. Skip"
    $choice = Read-Host "Select option (1-3)"
    
    switch ($choice) {
        "1" {
            $modelName = Read-Host "Enter model name (e.g., Product, User)"
            $fieldsJson = Read-Host "Enter fields JSON or path to JSON file"
            
            $addModelCmd = "python main.py backend add-model `"$ProjectPath`" $modelName -f '$fieldsJson'"
            Write-Host "`n> $addModelCmd" -ForegroundColor DarkGray
            Invoke-Expression $addModelCmd
        }
        "2" {
            $method = Read-Host "Enter HTTP method (GET, POST, PUT, DELETE)"
            $endpoint = Read-Host "Enter endpoint path (e.g., /api/products)"
            
            $addEndpointCmd = "python main.py backend add-endpoint `"$ProjectPath`" $method $endpoint"
            Write-Host "`n> $addEndpointCmd" -ForegroundColor DarkGray
            Invoke-Expression $addEndpointCmd
        }
        default {
            Write-Host "Skipping customizations..." -ForegroundColor Yellow
        }
    }
}

# ═════════════════════════════════════════════════════════════════════════
# STEP 5: AUTO-FIX (if enabled)
# ═════════════════════════════════════════════════════════════════════════

if ($AutoFix) {
    Write-Step "STEP 5: Auto-Fixing Code Issues"
    
    $backendPath = Join-Path $ProjectPath "backend"
    
    if (Test-Path $backendPath) {
        # Find all code files
        $codeFiles = Get-ChildItem -Path $backendPath -Recurse -Include *.js,*.ts,*.py |
            Where-Object { $_.FullName -notmatch "node_modules|__pycache__|\.git" } |
            Select-Object -First 5
        
        if ($codeFiles) {
            Write-Info "Found $($codeFiles.Count) files to check (showing first 5)"
            
            foreach ($file in $codeFiles) {
                $relativePath = $file.FullName.Replace($backendPath + "\", "")
                Write-Host "`nChecking: $relativePath" -ForegroundColor Cyan
                
                $fixCmd = "python main.py backend fix `"$backendPath`" -f `"$relativePath`""
                Write-Host "> $fixCmd" -ForegroundColor DarkGray
                
                Invoke-Expression $fixCmd
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Fixed: $relativePath"
                }
            }
        } else {
            Write-Host "No code files found to fix" -ForegroundColor Yellow
        }
    }
}

# ═════════════════════════════════════════════════════════════════════════
# COMPLETION SUMMARY
# ═════════════════════════════════════════════════════════════════════════

Write-Host "`n"
Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  🎉 BACKEND GENERATION WORKFLOW COMPLETE!" -ForegroundColor Green
Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Green

Write-Host "`n📂 Generated Files Location:" -ForegroundColor Cyan
Write-Host "   $ProjectPath\backend" -ForegroundColor White

Write-Host "`n📋 What was created:" -ForegroundColor Cyan
Write-Host "   ✓ Database schema and models"
Write-Host "   ✓ REST API endpoints"
Write-Host "   ✓ Business logic and services"
Write-Host "   ✓ Authentication/Authorization"
Write-Host "   ✓ Integration points"
Write-Host "   ✓ Tests and documentation"

Write-Host "`n🚀 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Review the generated code in the backend folder"
Write-Host "   2. Check the review report for any issues"
Write-Host "   3. Set up your database and environment variables"
Write-Host "   4. Run tests: cd backend && npm test (or pytest)"
Write-Host "   5. Start the server: npm start (or python app.py)"

Write-Host "`n💡 Useful Commands:" -ForegroundColor Cyan
Write-Host "   • Sync with frontend: python main.py backend sync `"$ProjectPath`""
Write-Host "   • Add model: python main.py backend add-model `"$ProjectPath`" ModelName"
Write-Host "   • Debug issues: python main.py backend debug `"$ProjectPath\backend`""
Write-Host "   • Rollback changes: python main.py backend rollback `"$ProjectPath`""

Write-Host "`n📊 Cost & Stats:" -ForegroundColor Cyan
Write-Host "   Run: python main.py stats" -ForegroundColor White

Write-Host "`n✨ Happy coding!" -ForegroundColor Yellow
Write-Host ""
