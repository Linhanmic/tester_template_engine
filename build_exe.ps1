# PowerShell 脚本：一键构建 CLI 单文件 exe（使用 PyInstaller）
# 使用方法：在项目根目录中以管理员或开发者 PowerShell 运行
#   .\build_exe.ps1 [-Clean] [-IncludeGUI]
# 参数：
#   -Clean: 清理上次构建的 dist 和 build 目录
#   -IncludeGUI: 同时尝试打包 GUI（需要安装 PyQt5，可能生成很大的 exe）

param(
    [switch]$Clean,
    [switch]$IncludeGUI
)

function Ensure-Package {
    param([string]$pkg)
    $installed = & pip show $pkg 2>$null
    if (-not $?) {
        Write-Host "正在安装 $pkg ..."
        & pip install $pkg
        if (-not $?) { throw "无法安装 $pkg" }
    } else {
        Write-Host "$pkg 已安装"
    }
}

if ($Clean) {
    Write-Host "清理上次构建..."
    Remove-Item -Recurse -Force dist,build -ErrorAction SilentlyContinue
    Remove-Item -Force *.spec -ErrorAction SilentlyContinue
}

# 确保 PyInstaller 可用（以及 jinja2）
Ensure-Package -pkg "pyinstaller"
Ensure-Package -pkg "jinja2"

# 构建 CLI 单文件 exe
Write-Host "开始打包 CLI (tester_template_engine.py) ..."
pyinstaller --onefile --console tester_template_engine.py --name "Tester模板生成器-CLI"
if ($LASTEXITCODE -ne 0) { Write-Error "CLI 打包失败（退出代码 $LASTEXITCODE）" ; exit $LASTEXITCODE }
Write-Host "CLI 打包完成，生成文件位于 dist\Tester模板生成器-CLI.exe"

if ($IncludeGUI) {
    Write-Host "开始尝试打包 GUI (gui.py) - 这可能会很慢且生成大文件..."
    Ensure-Package -pkg "pyqt5"
    pyinstaller --onefile --windowed gui.py --name "Tester模板生成器-GUI"
    if ($LASTEXITCODE -ne 0) { Write-Error "GUI 打包失败（退出代码 $LASTEXITCODE）" ; exit $LASTEXITCODE }
    Write-Host "GUI 打包完成，生成文件位于 dist\Tester模板生成器-GUI.exe"
}

Write-Host "构建完成。请查看 dist 目录中的可执行文件。"