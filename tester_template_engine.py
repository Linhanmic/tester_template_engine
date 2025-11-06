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
    """CAN信号编码解码类,处理CAN报文中的信号位域"""
    
    @staticmethod
    def generate_can_message(signal_spec: str) -> str:
        """从信号规范生成CAN报文指令
        
        Args:
            signal_spec: 格式为 "0x261,1.0-2.1=0x23A" 的信号规范
                         采用Intel字节序，低位字节在前
                         例如 1.0-2.1=0x23A 转换后为 3a 02 00 00 00 00 00 00
            
        Returns:
            str: 格式化的tcans命令
        """
        try:
            import re
            import logging
            logger = logging.getLogger(__name__)
            
            match = re.match(r"(0x[0-9A-Fa-f]+),([0-9]+)\.([0-9]+)-([0-9]+)\.([0-9]+)=(0x[0-9A-Fa-f]+)", signal_spec)
            if not match:
                raise ValueError(f"信号规范格式无效: {signal_spec}")

            can_id, start_byte, start_bit, end_byte, end_bit, value = match.groups()

            # 将十六进制值转换为整数
            value = int(value, 16)
            
            # 解析位域参数 (转换为0基索引)
            start_byte = int(start_byte) - 1  # 转换为0基索引
            start_bit = int(start_bit)
            end_byte = int(end_byte) - 1      # 转换为0基索引
            end_bit = int(end_bit)

            # 计算信号长度（总位数）
            signal_length = (end_byte - start_byte) * 8 + (end_bit - start_bit) + 1

            if signal_length <= 0 or signal_length > 64:
                raise ValueError(f"信号长度无效: {signal_length}")

            # 验证值是否超出信号长度能表示的范围
            max_value = (1 << signal_length) - 1
            if value > max_value:
                raise ValueError(f"值 {value} 超出信号长度 {signal_length} 位能表示的范围 (最大: {max_value})")

            # 初始化8字节数据
            msg_data = [0] * 8

            # 根据Intel字节序放置信号值
            # Intel格式：低位字节在前，位编号从LSB开始
            current_bit_pos = start_byte * 8 + start_bit
            
            for i in range(signal_length):
                # 检查当前信号位是否为1
                if value & (1 << i):
                    # 计算在CAN数据中的字节和位位置
                    byte_idx = current_bit_pos // 8
                    bit_idx = current_bit_pos % 8
                    
                    if byte_idx >= 8:
                        raise ValueError(f"位位置超出8字节范围: {byte_idx}")
                    
                    # 设置对应位为1
                    msg_data[byte_idx] |= (1 << bit_idx)
                
                current_bit_pos += 1

            # 转换数据为字符串格式
            msg_data_str = " ".join(f"{byte:02X}" for byte in msg_data)

            # 格式化CAN ID（去掉0x前缀）
            if can_id.startswith("0x"):
                can_id = can_id[2:]

            return f"tcans {can_id},{msg_data_str}"
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"生成CAN报文出错: {e}")
            raise
    
    @staticmethod
    def decode_can_message(can_id: str, data: str, signal_spec: str) -> int:
        """从CAN报文解码信号值
        
        Args:
            can_id: CAN报文ID
            data: CAN报文数据，格式为 "XX XX XX XX XX XX XX XX"
            signal_spec: 信号规范，格式为 "1.0-2.1"
            
        Returns:
            int: 解码出的信号值
        """
        try:
            import re
            # 解析信号规范
            match = re.match(r"([0-9]+)\.([0-9]+)-([0-9]+)\.([0-9]+)", signal_spec)
            if not match:
                raise ValueError(f"信号规范格式无效: {signal_spec}")

            start_byte, start_bit, end_byte, end_bit = match.groups()
            start_byte = int(start_byte) - 1  # 转换为0基索引
            start_bit = int(start_bit)
            end_byte = int(end_byte) - 1      # 转换为0基索引
            end_bit = int(end_bit)

            # 解析CAN数据
            data_bytes = [int(x, 16) for x in data.split()]
            if len(data_bytes) != 8:
                raise ValueError(f"CAN数据长度必须为8字节: {len(data_bytes)}")

            # 计算信号长度
            signal_length = (end_byte - start_byte) * 8 + (end_bit - start_bit) + 1

            # 提取信号值
            result = 0
            current_bit_pos = start_byte * 8 + start_bit
            
            for i in range(signal_length):
                byte_idx = current_bit_pos // 8
                bit_idx = current_bit_pos % 8
                
                if byte_idx >= 8:
                    raise ValueError(f"位位置超出8字节范围: {byte_idx}")
                
                # 检查对应位是否为1
                if data_bytes[byte_idx] & (1 << bit_idx):
                    result |= (1 << i)
                
                current_bit_pos += 1

            return result
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"解码CAN报文出错: {e}")
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
