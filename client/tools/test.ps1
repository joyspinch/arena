# 裂谷竞技 三段测试：
#   1) arena_test_OK          —— 玩法断言用例（波次/碰撞/战斗/补给/完整对局）
#   2) arena_SAVE_OK runs=1 -> runs=2 —— 存档写两遍读得到（第二遍是新进程）
#   3) arena_SMOKE_OK          —— 无头冒烟：跑满帧自行退出
#
# 用法：pwsh -File client/tools/test.ps1 [-PackageProject <包根>]
param(
    [string]$Compiler = $env:ZANC,
    [string]$PackageProject = '',
    [int]$TimeoutSeconds = 120
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $project
if (-not $Compiler) {
    $local = if ($env:ZAN_HOME) { Join-Path $env:ZAN_HOME 'build/zanc.exe' } else { '' }
    if ($local -and (Test-Path $local)) {
        $Compiler = $local
    } elseif (Test-Path 'D:/project/zan-lang/build/zanc.exe') {
        $Compiler = 'D:/project/zan-lang/build/zanc.exe'
    } else {
        $Compiler = (Get-Command zanc -ErrorAction Stop).Source
    }
}
if (-not $PackageProject) { if ($env:ZAN_HOME) { $PackageProject = $env:ZAN_HOME } else { throw '需要 $env:ZAN_HOME 指向 zan-lang 仓库（公共包在它的 packages/ 下），或用 -PackageProject 指定' } }
$out = Join-Path $repo 'build/arena'
& (Join-Path $PSScriptRoot 'build.ps1') -Compiler $Compiler -PackageProject $PackageProject -Output $out
$exe = Join-Path $out 'Arena.exe'
if (-not (Test-Path $exe)) { throw "缺少可执行文件：$exe" }

# --- 第一段：玩法断言用例 ---
# 源码要排除 main.zan（它带 Main()，用例自己的 Main 才是入口）。
$caseSources = @(Get-ChildItem (Join-Path $project 'src') -Recurse -File -Filter *.zan |
    Where-Object { $_.Name -ne 'main.zan' } |
    Sort-Object FullName | ForEach-Object { $_.FullName })
$case = 'arena_test.zan'
$stem = [IO.Path]::GetFileNameWithoutExtension($case)
$caseExe = Join-Path $out "$stem.exe"
& $Compiler (@((Join-Path $project "tests/$case")) + $caseSources +
    @('--auto-stdlib', '--package-project', $PackageProject, '-o', $caseExe))
if ($LASTEXITCODE -ne 0) { throw "玩法用例编译失败：$case (zanc=$LASTEXITCODE)" }
$caseOut = & $caseExe 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw "玩法用例失败：$case`n$caseOut" }
if ($caseOut -notmatch "$stem OK") { throw "玩法用例输出不对：$case`n$caseOut" }
Write-Host ($caseOut.Trim())
Write-Host "${stem}_OK"

# --- 第二、三段：无头冒烟 + 存档两遍 ---
# 存档落在临时目录里，不碰玩家机器上的 %LOCALAPPDATA%/Arena。
$saveDir = Join-Path $out 'savetest'
if (Test-Path $saveDir) { Remove-Item $saveDir -Recurse -Force }
New-Item -ItemType Directory -Force $saveDir | Out-Null
$env:ARENA_SAVE = $saveDir
# 冒烟标记：跑满 N 帧后程序自行退出（自动驾驶直接进对局，跑到真玩法上）。
$env:ARENA_SMOKE = '1'
$env:ARENA_FRAMES = '120'
$log = Join-Path $out 'arena_smoke.log'
if (Test-Path $log) { Remove-Item $log -Force }
$proc = Start-Process -FilePath $exe -WorkingDirectory $out -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $log -RedirectStandardError (Join-Path $out 'arena_smoke.err')
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    $proc.Kill()
    throw "无头冒烟超时：应用没在 $TimeoutSeconds 秒内退出"
}
if ($proc.ExitCode -ne 0) { throw "无头冒烟失败：exit=$($proc.ExitCode)" }
if (-not (Select-String -Path $log -Pattern 'ARENA_SMOKE_OK' -Quiet)) {
    throw "无头冒烟未收尾（缺 ARENA_SMOKE_OK）：$log"
}
$saveLine = Select-String -Path $log -Pattern 'ARENA_SAVE' | Select-Object -First 1
if (-not $saveLine) { throw "没有存档输出行（ARENA_SAVE）：$log" }
if ($saveLine.Line -notmatch 'runs=1') {
    throw "第一遍存档没写成局数 1：$($saveLine.Line)"
}
if (-not (Test-Path (Join-Path $saveDir 'arena_slot0.json'))) {
    throw "存档文件没落盘：$saveDir"
}
# 第二遍是新进程，必须读回第一遍写的档（局数 1 -> 2）。
$log2 = Join-Path $out 'arena_smoke2.log'
if (Test-Path $log2) { Remove-Item $log2 -Force }
$proc2 = Start-Process -FilePath $exe -WorkingDirectory $out -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $log2 -RedirectStandardError (Join-Path $out 'arena_smoke2.err')
if (-not $proc2.WaitForExit($TimeoutSeconds * 1000)) {
    $proc2.Kill()
    throw "第二遍无头冒烟超时"
}
if ($proc2.ExitCode -ne 0) { throw "第二遍无头冒烟失败：exit=$($proc2.ExitCode)" }
if (-not (Select-String -Path $log2 -Pattern 'ARENA_SMOKE_OK' -Quiet)) {
    throw "第二遍无头冒烟未收尾（缺 ARENA_SMOKE_OK）：$log2"
}
$saveLine2 = Select-String -Path $log2 -Pattern 'ARENA_SAVE' | Select-Object -First 1
if (-not $saveLine2 -or $saveLine2.Line -notmatch 'runs=2') {
    throw "第二遍没读回上一遍的存档（期望 runs=2）：$($saveLine2.Line)"
}
Write-Host "arena_SAVE_OK runs=1 -> runs=2"
Write-Host "arena_SMOKE_OK"
