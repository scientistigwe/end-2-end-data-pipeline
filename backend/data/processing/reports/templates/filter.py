# backend/data_pipeline/reporting/templates/filters.py

from typing import Any, Union
from datetime import datetime, timedelta
import json


def format_number(value: Union[int, float], precision: int = 2) -> str:
    """Format number with specified precision"""
    try:
        if isinstance(value, int):
            return f"{value:,}"
        return f"{value:,.{precision}f}"
    except (ValueError, TypeError):
        return str(value)


def format_percentage(value: float, precision: int = 1) -> str:
    """Format number as percentage"""
    try:
        return f"{value * 100:.{precision}f}%"
    except (ValueError, TypeError):
        return f"{value}%"


def format_duration(seconds: Union[int, float]) -> str:
    """Format duration in a human-readable format"""
    try:
        duration = timedelta(seconds=int(seconds))
        days = duration.days
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60

        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")

        return " ".join(parts) if parts else "0m"
    except (ValueError, TypeError):
        return str(seconds)


def format_datetime(dt_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime string"""
    try:
        if isinstance(dt_str, datetime):
            return dt_str.strftime(format)
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime(format)
    except (ValueError, TypeError):
        return dt_str


def format_json(value: Any, indent: int = 2) -> str:
    """Format value as JSON string"""
    try:
        return json.dumps(value, indent=indent)
    except Exception:
        return str(value)


def format_list(items: list, separator: str = ", ") -> str:
    """Format list as string with separator"""
    try:
        return separator.join(str(item) for item in items)
    except Exception:
        return str(items)


def truncate_text(text: str, length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    try:
        if len(text) <= length:
            return text
        return text[:length - len(suffix)] + suffix
    except Exception:
        return text


def status_class(status: str) -> str:
    """Get CSS class for status"""
    status_map = {
        'completed': 'success',
        'failed': 'error',
        'warning': 'warning',
        'pending': 'pending',
        'in_progress': 'info'
    }
    return status_map.get(status.lower(), 'default')


def metric_trend_class(value: float, threshold: float = 0) -> str:
    """Get CSS class for metric trend"""
    try:
        if value > threshold:
            return 'positive'
        elif value < -threshold:
            return 'negative'
        return 'neutral'
    except (ValueError, TypeError):
        return 'neutral'


def format_metric_value(value: Any, metric_type: str) -> str:
    """Format metric value based on type"""
    try:
        if metric_type == 'percentage':
            return format_percentage(float(value))
        elif metric_type == 'duration':
            return format_duration(float(value))
        elif metric_type == 'number':
            return format_number(float(value))
        elif metric_type == 'datetime':
            return format_datetime(value)
        return str(value)
    except (ValueError, TypeError):
        return str(value)


def format_chart_data(data: dict) -> dict:
    """Format data for chart rendering"""
    try:
        if not isinstance(data, dict):
            return data

        formatted_data = data.copy()
        if 'values' in formatted_data:
            formatted_data['values'] = [
                format_number(v) if isinstance(v, (int, float)) else v
                for v in formatted_data['values']
            ]

        if 'labels' in formatted_data:
            formatted_data['labels'] = [str(l) for l in formatted_data['labels']]

        return formatted_data
    except Exception:
        return data


def severity_class(severity: str) -> str:
    """Get CSS class for severity level"""
    severity_map = {
        'critical': 'critical',
        'high': 'high',
        'medium': 'medium',
        'low': 'low'
    }
    return severity_map.get(severity.lower(), 'default')


def confidence_class(confidence: float) -> str:
    """Get CSS class for confidence level"""
    try:
        if confidence >= 0.8:
            return 'high'
        elif confidence >= 0.5:
            return 'medium'
        return 'low'
    except (ValueError, TypeError):
        return 'medium'


def format_key_value_pairs(data: dict, separator: str = ": ") -> List[str]:
    """Format dictionary into list of key-value strings"""
    try:
        return [
            f"{key}{separator}{value}"
            for key, value in data.items()
        ]
    except Exception:
        return []


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    try:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
    except (ValueError, TypeError):
        return str(size_bytes)


def register_filters(env):
    """Register all custom filters with Jinja environment"""
    filters = {
        'format_number': format_number,
        'format_percentage': format_percentage,
        'format_duration': format_duration,
        'format_datetime': format_datetime,
        'format_json': format_json,
        'format_list': format_list,
        'truncate_text': truncate_text,
        'status_class': status_class,
        'metric_trend_class': metric_trend_class,
        'format_metric_value': format_metric_value,
        'format_chart_data': format_chart_data,
        'severity_class': severity_class,
        'confidence_class': confidence_class,
        'format_key_value_pairs': format_key_value_pairs,
        'format_size': format_size
    }

    for name, func in filters.items():
        env.filters[name] = func