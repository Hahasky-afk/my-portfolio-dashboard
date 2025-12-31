$ErrorActionPreference = "Stop"

# 配置路径
$WorkDir = "c:\Users\K.Young\Desktop\antigravity_backup\01-system\tools\ibkr-dashboard"
$PythonPath = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"

# 记录日志
$LogFile = "$WorkDir\auto_update.log"
function Log($Message) {
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Timestamp - $Message" | Out-File -FilePath $LogFile -Append
}

Log "Starting auto-update..."

try {
    Set-Location $WorkDir
    
    # 1. 运行 Python 脚本更新数据
    Log "Running main.py..."
    & $PythonPath main.py 2>&1 | Out-File -FilePath $LogFile -Append
    
    # 2. 检查 Git 状态
    $GitStatus = git status --porcelain
    if ($GitStatus) {
        Log "Changes detected. Committing..."
        git add dashboard/data.json dashboard/history.json
        git commit -m "Auto-update portfolio data (Local Scheduler)"
        Log "Pushing to GitHub..."
        git push
        Log "Push successful."
    } else {
        Log "No changes detected."
    }
    
    Log "Auto-update completed successfully."
} catch {
    Log "Error: $_"
    exit 1
}
