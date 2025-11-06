#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tester语言模板引擎 - 用于自动生成Tester语言测试脚本
基于提供的模板和数据源，可灵活生成符合Tester语言规范的测试用例
"""

import re
import csv
import argparse
from typing import Dict, List, Tuple, Any, Optional, Union
import os
import logging
import sys
from jinja2 import Environment, FileSystemLoader, Template

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TesterTemplateEngine")

class TesterSignal:
    """CAN信号编码解码类，处理CAN报文中的信号位域"""
    
    @staticmethod
    def generate_can_message(signal_spec: str) -> str:
        """从信号规范生成CAN报文指令
        
        Args:
            signal_spec: 格式为 "0x261,1.0-2.1=0x12A" 的信号规范
            
        Returns:
            str: 格式化的tcans命令
        """
        # 从信号规范中提取CAN ID和值
        try:
            # 使用简单的字符串分割来获取值
            id_part, value_part = signal_spec.split("=")
            can_id = id_part.split(",")[0]
            
            # 将十六进制值转换为整数
            value = int(value_part.strip(), 16)
            
            # 生成CAN报文 - 简化为固定格式
            # 假设值永远放在第一个字节，其他字节为0
            msg_data = f"{value:02x} 01 00 00 00 00 00 00"
            
            # 如果CAN ID是十六进制格式，去掉0x前缀
            if can_id.startswith("0x"):
                can_id = can_id[2:]
                
            return f"tcans {can_id},{msg_data}"
        except Exception as e:
            logger.error(f"生成CAN报文出错: {e}")
            raise


class TemplateEngine:
    """Tester语言模板引擎，用于解析模板并生成测试脚本"""
    
    def __init__(self):
        self.variables = {}  # 存储模板变量
        self.templates = {}  # 存储模板定义
    
    def load_variables_from_csv(self, file_path: str, key_column: int = 0, value_column: int = 1, 
                               has_header: bool = True, var_name: str = None) -> None:
        """从CSV文件加载变量
        
        Args:
            file_path: CSV文件路径
            key_column: 键列索引
            value_column: 值列索引
            has_header: 是否有标题行
            var_name: 变量名，如不指定则使用文件名
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到文件: {file_path}")
            
        if var_name is None:
            var_name = os.path.splitext(os.path.basename(file_path))[0]
            
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            # 尝试自动检测分隔符
            sample = f.readline()
            if ';' in sample:
                delimiter = ';'
            else:
                delimiter = ','
            f.seek(0)  # 回到文件开头
            
            reader = csv.reader(f, delimiter=delimiter)
            if has_header:
                next(reader)  # 跳过标题行
                
            for row in reader:
                if len(row) > max(key_column, value_column):
                    # 保存为元组对
                    data.append((row[key_column], row[value_column]))
                    
        self.variables[var_name] = data
        logger.info(f"从 {file_path} 加载了 {len(data)} 条数据到变量 {var_name}")
    

    
    def load_template_from_file(self, file_path: str, template_name: str = None) -> None:
        """从文件加载模板
        
        Args:
            file_path: 模板文件路径
            template_name: 模板名称，如不指定则使用文件名
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到文件: {file_path}")
            
        if template_name is None:
            template_name = os.path.splitext(os.path.basename(file_path))[0]
            
        with open(file_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
            
        self.templates[template_name] = template_content
        logger.info(f"从 {file_path} 加载了模板 {template_name}")
    
    def register_template(self, template_name: str, template_content: str) -> None:
        """注册模板
        
        Args:
            template_name: 模板名称
            template_content: 模板内容
        """
        self.templates[template_name] = template_content
        logger.info(f"注册了模板 {template_name}")
    
    def register_variable(self, var_name: str, var_value: Any) -> None:
        """注册变量
        
        Args:
            var_name: 变量名
            var_value: 变量值
        """
        self.variables[var_name] = var_value
        logger.info(f"注册了变量 {var_name}")
    
    def parse_template_variables(self, template: str) -> List[str]:
        """解析模板中的变量引用
        
        Args:
            template: 模板内容
            
        Returns:
            List[str]: 模板中引用的变量名列表
        """
        # 匹配 <variable_name> 格式的变量
        pattern = r"<([^>]+)>"
        matches = re.findall(pattern, template)
        return matches
    
    def render_template(self, template_name: str, output_file: str = None) -> str:
        """渲染模板并生成测试脚本
        
        Args:
            template_name: 模板名称
            output_file: 输出文件路径，如不指定则只返回渲染结果
            
        Returns:
            str: 渲染后的测试脚本内容
        """
        if template_name not in self.templates:
            raise KeyError(f"未找到模板: {template_name}")
            
        template_content = self.templates[template_name]
        
        try:
            # 创建Jinja2模板环境
            env = Environment()
            # 添加内置函数到模板环境
            env.globals.update({
                'len': len,
                'enumerate': enumerate,
                'range': range,
                'str': str,
                'int': int
            })
            template = env.from_string(template_content)
            
            # 渲染模板
            result = template.render(**self.variables)
            
            # 写入输出文件
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result)
                logger.info(f"已将渲染结果写入文件: {output_file}")
            
            return result
            
        except Exception as e:
            logger.error(f"渲染模板时出错: {e}")
            raise


class TesterScriptGenerator:
    """Tester语言测试脚本生成器，集成模板引擎和信号处理功能"""
    
    def __init__(self):
        self.template_engine = TemplateEngine()
    
    def load_data_from_csv(self, file_path: str, var_name: str = None) -> None:
        """加载CSV数据
        
        Args:
            file_path: CSV文件路径
            var_name: 变量名，如不指定则使用文件名
        """
        self.template_engine.load_variables_from_csv(file_path, var_name=var_name)
    
    def load_template(self, file_path: str, template_name: str = None) -> None:
        """加载模板
        
        Args:
            file_path: 模板文件路径
            template_name: 模板名称，如不指定则使用文件名
        """
        self.template_engine.load_template_from_file(file_path, template_name)
    
    def generate_script(self, template_name: str, output_file: str) -> None:
        """生成测试脚本
        
        Args:
            template_name: 模板名称
            output_file: 输出文件路径
        """
        # 注册辅助函数到模板引擎
        self.template_engine.register_variable("encode_signal", TesterSignal.generate_can_message)
        
        # 渲染模板并生成脚本
        self.template_engine.render_template(template_name, output_file)
        logger.info(f"成功生成测试脚本: {output_file}")


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description="Tester语言模板测试脚本生成器")
    parser.add_argument("--template", "-t", required=True, help="模板文件路径")
    parser.add_argument("--output", "-o", required=True, help="输出文件路径")
    parser.add_argument("--data", "-d", nargs="+", required=True, help="CSV数据文件路径列表，可指定多个")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        generator = TesterScriptGenerator()
        
        # 加载所有CSV数据文件
        for data_file in args.data:
            var_name = os.path.splitext(os.path.basename(data_file))[0]
            generator.load_data_from_csv(data_file, var_name)
        
        # 加载模板并生成脚本
        generator.load_template(args.template)
        template_name = os.path.splitext(os.path.basename(args.template))[0]
        generator.generate_script(template_name, args.output)
        
        print(f"成功生成测试脚本: {args.output}")
        return 0
        
    except Exception as e:
        logger.error(f"生成脚本时出错: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
