import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
import os
import logging
from datetime import datetime
import numpy as np

# 创建日志记录器
logger = logging.getLogger(__name__)

class ExcelService:
    def __init__(self):
        logger.info("ExcelService initialized")

    def parse_excel_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        解析Excel文件为JSON数组
        """
        logger.info(f"Parsing Excel file: {file_path}")
        
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        try:
            df = pd.read_excel(file_path)
            logger.info(f"Successfully read Excel file: {file_path}, {len(df)} rows, {len(df.columns)} columns")
            data = df.to_dict('records')
            logger.info(f"Converted Excel data to {len(data)} records")
            return data
        except Exception as e:
            error_msg = f"Failed to read Excel file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def save_uploaded_file(self, file) -> str:
        """
        保存上传的Excel文件并返回路径
        """
        logger.info(f"Saving uploaded file: {file.filename}")
        
        upload_dir = os.getenv('UPLOAD_DIR', './public/uploads')
        logger.debug(f"Upload directory: {upload_dir}")
        os.makedirs(upload_dir, exist_ok=True)
        
        file_name = f"{int(pd.Timestamp.now().timestamp())}-{file.filename}"
        file_path = os.path.join(upload_dir, file_name)
        
        # 保存文件
        logger.info(f"Saving file to: {file_path}")
        with open(file_path, 'wb') as f:
            f.write(file.file.read())
        
        logger.info(f"File saved successfully: {file_path}")
        
        # 删除临时文件
        if hasattr(file, 'temp_file') and os.path.exists(file.temp_file):
            logger.info(f"Deleting temporary file: {file.temp_file}")
            os.unlink(file.temp_file)
        
        return file_path

    def get_excel_structure(self, file_path: str) -> Dict[str, Any]:
        """
        解析 Excel 文件结构
        返回所有 Sheet 名称和行数
        """
        logger.info(f"Getting Excel structure for: {file_path}")
        
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        try:
            # 使用 ExcelFile 对象来获取所有 sheet 信息
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            sheets_info = []
            for sheet_name in sheet_names:
                # 读取每个 sheet 的基本信息
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                sheet_info = {
                    "name": sheet_name,
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns)
                }
                sheets_info.append(sheet_info)
            
            structure = {
                "file_path": file_path,
                "sheet_count": len(sheet_names),
                "sheets": sheets_info
            }
            
            logger.info(f"Excel structure parsed: {len(sheet_names)} sheets")
            return structure
            
        except Exception as e:
            error_msg = f"Failed to parse Excel structure {file_path}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_sheet_data(self, file_path: str, sheet_name: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        读取指定 Sheet 的数据
        """
        logger.info(f"Reading sheet data: {file_path}, sheet: {sheet_name}")
        
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        try:
            # 读取指定 sheet
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # 如果指定了限制行数
            if limit and limit > 0:
                df = df.head(limit)
            
            # 处理空值和特殊字符
            df = self._clean_dataframe(df)
            
            # 转换为字典格式
            data = df.to_dict('records')
            
            result = {
                "sheet_name": sheet_name,
                "row_count": len(data),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "data": data
            }
            
            logger.info(f"Sheet data read successfully: {len(data)} rows")
            return result
            
        except Exception as e:
            error_msg = f"Failed to read sheet data {file_path}:{sheet_name}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def infer_field_types(self, file_path: str, sheet_name: str) -> List[Dict[str, Any]]:
        """
        自动推断字段类型（文本/数字/日期）
        """
        logger.info(f"Inferring field types: {file_path}, sheet: {sheet_name}")
        
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            field_types = []
            for column in df.columns:
                field_info = {
                    "field_name": column,
                    "display_name": column,
                    "data_type": self._infer_column_type(df[column]),
                    "is_nullable": df[column].isnull().any(),
                    "sample_values": self._get_sample_values(df[column]),
                    "unique_count": df[column].nunique(),
                    "null_count": df[column].isnull().sum()
                }
                field_types.append(field_info)
            
            logger.info(f"Field types inferred for {len(field_types)} columns")
            return field_types
            
        except Exception as e:
            error_msg = f"Failed to infer field types {file_path}:{sheet_name}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理空值和特殊字符
        """
        # 替换 NaN 为 None
        df = df.where(pd.notnull(df), None)
        
        # 处理字符串列中的特殊字符
        for column in df.select_dtypes(include=['object']).columns:
            df[column] = df[column].astype(str).replace('nan', None)
            # 去除前后空格
            df[column] = df[column].apply(lambda x: x.strip() if isinstance(x, str) and x != 'None' else x)
            # 将空字符串转换为 None
            df[column] = df[column].replace('', None)
        
        return df

    def _infer_column_type(self, series: pd.Series) -> str:
        """
        推断列的数据类型
        """
        # 去除空值进行类型推断
        non_null_series = series.dropna()
        
        if len(non_null_series) == 0:
            return "TEXT"
        
        # 尝试转换为数字
        try:
            pd.to_numeric(non_null_series)
            # 检查是否为整数
            if all(float(x).is_integer() for x in non_null_series if pd.notnull(x)):
                return "INTEGER"
            else:
                return "DECIMAL"
        except (ValueError, TypeError):
            pass
        
        # 尝试转换为日期
        try:
            pd.to_datetime(non_null_series)
            return "DATETIME"
        except (ValueError, TypeError):
            pass
        
        # 检查是否为布尔值
        unique_values = set(str(x).lower() for x in non_null_series.unique())
        if unique_values.issubset({'true', 'false', '1', '0', 'yes', 'no'}):
            return "BOOLEAN"
        
        # 默认为文本类型
        return "TEXT"

    def _get_sample_values(self, series: pd.Series, limit: int = 5) -> List[Any]:
        """
        获取列的示例值
        """
        non_null_values = series.dropna().unique()
        sample_values = list(non_null_values[:limit])
        return sample_values