# Tester 语言模板引擎

这个工具包是为了简化 Tester 语言测试脚本的生成而设计的。通过提供模板和数据源，可以批量生成符合 Tester 语言规范的测试脚本。

## 功能特点

- 灵活的模板系统，支持变量替换和条件逻辑
- 强大的信号编码功能，支持 CAN 报文位域的精确控制
- 多种数据源支持，包括 CSV 和 JSON
- 内置语法验证，确保生成的脚本符合 Tester 语言规范
- 命令行工具和 API 接口双重支持

## 安装方法

将所有文件下载到同一目录即可使用，无需额外安装依赖。

## 使用方法

### 命令行使用

基本用法:

```bash
python tester_template_engine.py --template 模板文件 --output 输出文件 --data 数据文件1 数据文件2 ... [--verbose]
```

参数说明:

- `--template, -t`: 模板文件路径（必需）
- `--output, -o`: 输出文件路径（必需）
- `--data, -d`: 一个或多个 CSV 数据文件路径（必需，按文件名作为模板变量名）
- `--verbose, -v`: 显示详细日志（可选）

示例:

```bash
python tester_template_engine.py --template 文字提示模板.txt --output 测试脚本.tester --data 文字提示.csv 电源挡位.csv 故障码.csv
```

### 在 Python 代码中使用

```python
from tester_template_engine import TesterScriptGenerator

# 创建生成器实例
generator = TesterScriptGenerator()

# 加载 CSV 数据文件（可以调用多次，默认以文件名（不含扩展）作为变量名）
generator.load_data_from_csv("文字提示.csv")
generator.load_data_from_csv("电源挡位.csv")

# 加载模板并生成脚本
generator.load_template("文字提示模板.txt")
template_name = "文字提示模板"  # 通常使用文件名
generator.generate_script(template_name, "文字提示测试.tester")
```

### 示例脚本

使用示例脚本可以快速生成预定义的测试案例:

```bash
python generate_example.py --type all
```

## 模板语法

### 基本变量替换

使用 `{{ 变量名 }}` 语法进行变量替换:

```
tdiagnose_rid {{ 诊断请求ID }}
```

### 循环结构

使用 `{% for ... %}` 和 `{% endfor %}` 进行循环:

```
{% for i in range(len(文字提示)) %}
ttitle={{ i+1 }}、{{ 文字提示[i][1] }}
  // ... 测试用例内容
ttitle-end
{% endfor %}
```

### 条件结构

使用 `{% if ... %}`, `{% elif ... %}`, `{% else %}` 和 `{% endif %}` 进行条件判断:

```
{% if 步骤.类型 == "发送" %}
tcans {{ 步骤.通道 if 步骤.通道 else "0" }},{{ 步骤.ID }},{{ 步骤.数据 }},{{ 步骤.间隔 }},{{ 步骤.次数 }}
{% elif 步骤.类型 == "接收" %}
tcanr {{ 步骤.通道 if 步骤.通道 else "0" }},{{ 步骤.ID }},{{ 步骤.位域 }},{{ 步骤.期望值 if 步骤.期望值 else "print" }},{{ 步骤.超时 }}
{% endif %}
```

### 内置函数

使用 `{{ encode_signal("0x123,1.0-2.3=0x45") }}` 可以生成符合位域规范的 CAN 报文。

### 数据文件格式

CSV 文件默认会把第一列作为键、第二列作为值，，并把整个文件以列表形式注册为模板变量（变量名默认为文件名，不含扩展名）。示例：

```csv
提示值,提示内容
0x12A,发动机启动中
0x12B,变速箱故障
```

备注：新版已移除 JSON 配置文件支持，建议把配置信息拆成 CSV 文件并直接传入 `--data`。

## 打包为离线单文件可执行程序（Windows .exe）

下面提供将工具打包为单文件 Windows 可执行程序的说明与脚本示例。打包会把 Python 解释器和所有依赖打包到一个 exe 中，用户无需在目标机器上安装 Python 或其他库。

注意与建议：

- 推荐先只打包 CLI（`tester_template_engine.py`），因为 GUI（基于 PyQt5）体积更大并且可能需要额外的 hook 配置。
- 打包前建议在清洁的虚拟环境中安装依赖以获得更小的可执行文件。
- 打包过程会产出 `dist/` 目录，里面包含单文件 exe。生成的 exe 在其他 Windows 机器上通常可直接运行。

下面示例使用 PyInstaller（以 Windows PowerShell 为例）：

1. 在开发机器上准备虚拟环境并安装依赖：

```powershell
# 创建并激活虚拟环境（可选）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装最低依赖（仅用于 CLI 打包）
pip install jinja2 pyinstaller
```

2. 使用 PyInstaller 打包（CLI 单文件）：

```powershell
# 在项目根目录运行（包含 tester_template_engine.py）
pyinstaller --onefile --console tester_template_engine.py
# 可执行文件位于 dist\tester_template_engine.exe
```

3. 可选：为 GUI 打包（体积较大且可能需额外 hook）：

```powershell
# 安装 PyQt5 后运行（需要更多时间和空间）
pip install pyqt5 pyinstaller jinja2
pyinstaller --onefile --windowed gui.py
# 生成 dist\gui.exe
```

常见问题（FAQ）

- 打包后 exe 无法找到模板或 CSV：请确保在运行 exe 时以当前工作目录传入模板路径和数据文件（exe 不会自动包含外部用户数据，除非你在 pyinstaller 命令中使用 `--add-data` 将这些文件一起打包）。
- 打包后程序缺少模块（如 jinja2 hooks）：尝试在 PyInstaller 命令中使用 `--hidden-import jinja2` 或查看 PyInstaller 的运行日志并补充 `--hidden-import`。

仓库中也包含一个示例打包脚本 `build_exe.ps1`（仅用于自动化 CLI 打包步骤）。

如果你希望我现在尝试在此环境中构建 CLI exe，请回复“现在构建 CLI exe”，我将：

1. 安装 PyInstaller（如未安装）
2. 运行 pyinstaller --onefile --console tester_template_engine.py
3. 报告构建日志并列出生成的 exe 路径

## 使用示例

此工具包中包含以下示例文件：

- `文字提示模板.txt`: 文字提示测试模板
- `文字提示.csv`: 文字提示数据
- `tester_config.json`: 基本配置数据
- `诊断测试模板.txt`: 诊断功能测试模板
- `诊断测试配置.json`: 诊断测试配置数据
- `generate_example.py`: 示例脚本生成器

## 高级功能

### 自定义辅助函数

可以在 Python 代码中注册自定义函数到模板引擎：

```python
def my_custom_function(arg):
    # 处理逻辑
    return result

generator.template_engine.register_variable("my_function", my_custom_function)
```

然后在模板中使用：

```
{{ my_function(参数) }}
```

### 模板验证

引擎会自动验证生成的测试脚本是否符合 Tester 语言规范，并在日志中输出警告信息。

## 常见问题解答

**Q: 如何处理复杂的位域编码？**
A: 使用 `encode_signal` 函数，它支持精确的位域控制，例如：

```
{{ encode_signal("0x123,1.0-2.3=0x45") }}
```

**Q: 如何在模板中执行 Python 表达式？**
A: 使用 `{{ }}` 语法包裹表达式，例如：

```
{{ 变量 * 2 + 1 }}
```

**Q: 如何处理大规模数据？**
A: 可以使用外部数据库或分块处理大量数据，然后分别生成测试脚本。

## 限制与注意事项

- 模板引擎不支持递归调用
- 对于非常复杂的逻辑，建议在 Python 代码中处理后再传递到模板
- 生成的测试脚本需要人工审核以确保正确性

## 联系与支持

如有问题或建议，请提交 Issue 或发送邮件至维护者。

## 许可证

MIT 许可证
