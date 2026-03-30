# GitHub Talent Finder - Production Start Script (Windows)
# Run this script to launch the application with multi-worker concurrency.

Write-Host "🚀 Launching GitHub Talent Finder in Production Mode..." -ForegroundColor Cyan

# Define number of workers (recommend: 2 * Cores + 1)
$CPU_CORES = (Get-WmiObject Win32_Processor).NumberOfCores
$WORKERS = ($CPU_CORES * 2) + 1
Write-Host "🔧 Configured for $WORKERS worker processes." -ForegroundColor Gray

# Run Uvicorn with multiple workers
# Note: --reload is disabled in production for performance and stability.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers $WORKERS --log-level info

Write-Host "✅ Application shutdown complete." -ForegroundColor Yellow
