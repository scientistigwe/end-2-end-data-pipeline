# backend/utils/formatters.py

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
import json
import pandas as pd
import numpy as np
from enum import Enum


class DataFormat(Enum):
    """Standard data formats"""
    JSON = "json"
    CSV = "csv"
    YAML = "yaml"
    XML = "xml"
    HTML = "html"
    MARKDOWN = "markdown"


class DateTimeFormatter:
    """DateTime formatting utilities"""

    DEFAULT_DATE_FORMAT = "%Y-%m-%d"
    DEFAULT_TIME_FORMAT = "%H:%M:%S"
    DEFAULT_DATETIME_FORMAT = f"{DEFAULT_DATE_FORMAT} {DEFAULT_TIME_FORMAT}"

    @staticmethod
    def format_date(value: Union[date, datetime, str],
                    format_str: Optional[str] = None) -> str:
        """Format date value"""
        try:
            if isinstance(value, str):
                # Parse string to datetime first
                value = pd.to_datetime(value)

            return value.strftime(format_str or DateTimeFormatter.DEFAULT_DATE_FORMAT)
        except Exception as e:
            return str(value)

    @staticmethod
    def format_datetime(value: Union[datetime, str],
                        format_str: Optional[str] = None) -> str:
        """Format datetime value"""
        try:
            if isinstance(value, str):
                # Parse string to datetime first
                value = pd.to_datetime(value)

            return value.strftime(format_str or DateTimeFormatter.DEFAULT_DATETIME_FORMAT)
        except Exception as e:
            return str(value)

    @staticmethod
    def format_timestamp(value: Union[datetime, str, float]) -> str:
        """Format timestamp to ISO format"""
        try:
            if isinstance(value, (int, float)):
                value = datetime.fromtimestamp(value)
            elif isinstance(value, str):
                value = pd.to_datetime(value)

            return value.isoformat()
        except Exception as e:
            return str(value)


class NumericFormatter:
    """Numeric formatting utilities"""

    @staticmethod
    def format_number(value: Union[int, float],
                      decimals: int = 2,
                      thousands_sep: str = ",") -> str:
        """Format numeric value"""
        try:
            if isinstance(value, (int, float)):
                return f"{value:,.{decimals}f}"
            return str(value)
        except Exception as e:
            return str(value)

    @staticmethod
    def format_percentage(value: float,
                          decimals: int = 2,
                          include_sign: bool = True) -> str:
        """Format percentage value"""
        try:
            formatted = f"{value:.{decimals}f}"
            return f"{formatted}%" if include_sign else formatted
        except Exception as e:
            return str(value)

    @staticmethod
    def format_currency(value: float,
                        currency: str = "$",
                        decimals: int = 2,
                        thousands_sep: str = ",") -> str:
        """Format currency value"""
        try:
            formatted = f"{abs(value):,.{decimals}f}"
            if value < 0:
                return f"-{currency}{formatted}"
            return f"{currency}{formatted}"
        except Exception as e:
            return str(value)


class DataFrameFormatter:
    """DataFrame formatting utilities"""

    @staticmethod
    def format_dataframe(df: pd.DataFrame,
                         format_rules: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """Format DataFrame columns according to rules"""
        formatted_df = df.copy()

        for column, rules in format_rules.items():
            if column not in formatted_df.columns:
                continue

            format_type = rules.get('type', 'string')

            if format_type == 'date':
                formatted_df[column] = formatted_df[column].apply(
                    lambda x: DateTimeFormatter.format_date(x, rules.get('format'))
                )
            elif format_type == 'datetime':
                formatted_df[column] = formatted_df[column].apply(
                    lambda x: DateTimeFormatter.format_datetime(x, rules.get('format'))
                )
            elif format_type == 'number':
                formatted_df[column] = formatted_df[column].apply(
                    lambda x: NumericFormatter.format_number(
                        x,
                        decimals=rules.get('decimals', 2),
                        thousands_sep=rules.get('thousands_sep', ',')
                    )
                )
            elif format_type == 'percentage':
                formatted_df[column] = formatted_df[column].apply(
                    lambda x: NumericFormatter.format_percentage(
                        x,
                        decimals=rules.get('decimals', 2),
                        include_sign=rules.get('include_sign', True)
                    )
                )
            elif format_type == 'currency':
                formatted_df[column] = formatted_df[column].apply(
                    lambda x: NumericFormatter.format_currency(
                        x,
                        currency=rules.get('currency', '$'),
                        decimals=rules.get('decimals', 2)
                    )
                )

        return formatted_df

    @staticmethod
    def format_pivot_table(df: pd.DataFrame,
                           index: Union[str, List[str]],
                           columns: Optional[Union[str, List[str]]] = None,
                           values: Optional[Union[str, List[str]]] = None,
                           aggregation: str = 'sum') -> pd.DataFrame:
        """Create and format pivot table"""
        try:
            pivot = pd.pivot_table(
                df,
                index=index,
                columns=columns,
                values=values,
                aggfunc=aggregation
            )

            # Reset index for easier handling
            if isinstance(index, list) and len(index) > 1:
                pivot = pivot.reset_index()

            return pivot
        except Exception as e:
            return df


class OutputFormatter:
    """Output formatting utilities"""

    @staticmethod
    def format_json(data: Any,
                    indent: int = 2,
                    ensure_ascii: bool = False) -> str:
        """Format data as JSON"""
        try:
            if isinstance(data, pd.DataFrame):
                data = data.to_dict('records')
            return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
        except Exception as e:
            return str(data)

    @staticmethod
    def format_csv(data: Union[pd.DataFrame, List[Dict[str, Any]]],
                   separator: str = ",") -> str:
        """Format data as CSV"""
        try:
            if not isinstance(data, pd.DataFrame):
                data = pd.DataFrame(data)
            return data.to_csv(index=False, sep=separator)
        except Exception as e:
            return str(data)

    @staticmethod
    def format_markdown_table(data: Union[pd.DataFrame, List[Dict[str, Any]]]) -> str:
        """Format data as Markdown table"""
        try:
            if not isinstance(data, pd.DataFrame):
                data = pd.DataFrame(data)

            # Create header
            headers = data.columns
            header_row = "| " + " | ".join(headers) + " |"
            separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"

            # Create rows
            rows = []
            for _, row in data.iterrows():
                rows.append("| " + " | ".join(str(x) for x in row) + " |")

            # Combine all parts
            return "\n".join([header_row, separator_row] + rows)
        except Exception as e:
            return str(data)

    @staticmethod
    def format_html_table(data: Union[pd.DataFrame, List[Dict[str, Any]]],
                          classes: Optional[str] = None) -> str:
        """Format data as HTML table"""
        try:
            if not isinstance(data, pd.DataFrame):
                data = pd.DataFrame(data)
            return data.to_html(
                classes=classes,
                index=False,
                escape=True,
                table_id="data-table"
            )
        except Exception as e:
            return str(data)


class MessageFormatter:
    """Message formatting utilities"""

    @staticmethod
    def format_error_message(error: Exception,
                             include_traceback: bool = False) -> Dict[str, Any]:
        """Format error message"""
        return {
            'error_type': error.__class__.__name__,
            'message': str(error),
            'traceback': str(error.__traceback__) if include_traceback else None,
            'timestamp': datetime.now().isoformat()
        }

    @staticmethod
    def format_status_message(status: str,
                              details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format status message"""
        return {
            'status': status,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }

    @staticmethod
    def format_progress_message(current: int,
                                total: int,
                                status: str = "in_progress") -> Dict[str, Any]:
        """Format progress message"""
        percentage = (current / total * 100) if total > 0 else 0
        return {
            'current': current,
            'total': total,
            'percentage': round(percentage, 2),
            'status': status,
            'timestamp': datetime.now().isoformat()
        }