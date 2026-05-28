import os
import ast

def get_module_info(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None, []

    docstring = ast.get_docstring(tree)
    
    functions = []
    classes = []
    
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            func_doc = ast.get_docstring(node)
            functions.append({
                'name': node.name,
                'doc': func_doc.split('\n')[0] if func_doc else '无注释'
            })
        elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
            class_doc = ast.get_docstring(node)
            classes.append({
                'name': node.name,
                'doc': class_doc.split('\n')[0] if class_doc else '无注释'
            })
            
    return docstring, classes, functions

base_dir = r"d:\codex\metallocene-epdm-digital-twin\epdm_sim"

output_lines = [
    "# Metallocene EPDM Digital Twin - 全量文件与功能技术说明",
    "",
    "本文档通过遍历工程源码 `epdm_sim` 目录下的所有核心文件，自动提取了底层实现的类与功能清单，为您提供一份极其详尽的技术架构与接口参考。",
    "",
    "## 核心目录概览",
    "- **`math_core/` & `solver_core/`**: 底层数值求解与非线性约束引擎",
    "- **`dynamic_core/`**: DAE、微分求解与动态事件管理",
    "- **`flowsheet_core/` & `fluid_core/` & `reactor_core/`**: 化工过程模拟、流体力学与反应器核心",
    "- **`estimation/`**: 残差感知优化与参数标定",
    "- **`pages/` & `ui_components/`**: Streamlit 交互与前端呈现",
    "",
    "---",
    "## 模块与文件级功能详述",
    ""
]

for root, dirs, files in os.walk(base_dir):
    # skip __pycache__ etc
    if "__pycache__" in root or ".pytest_cache" in root:
        continue
        
    for file in files:
        if file.endswith('.py') and file != "__init__.py":
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, base_dir)
            
            docstring, classes, functions = get_module_info(filepath)
            
            if not classes and not functions:
                continue
                
            output_lines.append(f"### 文件: `{rel_path}`")
            if docstring:
                clean_doc = docstring.split('\n')[0]
                output_lines.append(f"**模块描述**: {clean_doc}")
            
            if classes:
                output_lines.append("\n**核心类定义 (Classes)**:")
                for cls in classes:
                    output_lines.append(f"- `{cls['name']}`: {cls['doc']}")
            
            if functions:
                output_lines.append("\n**开放函数接口 (Functions)**:")
                for func in functions:
                    output_lines.append(f"- `{func['name']}()`: {func['doc']}")
            
            output_lines.append("\n---\n")

md_path = r"d:\codex\metallocene-epdm-digital-twin\README_Deep_Technical.md"

with open(md_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f"Successfully generated {md_path}")
