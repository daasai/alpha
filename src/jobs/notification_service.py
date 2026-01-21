"""
Notification Service - 通知服务

支持多种通知渠道：
- 日志通知（必须）
- 邮件通知（可选）
- 系统通知（macOS/Linux）
"""
import smtplib
import platform
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.logging_config import get_logger

logger = get_logger(__name__)


class NotificationService:
    """通知服务"""
    
    def __init__(
        self,
        enabled: bool = True,
        channels: Optional[List[str]] = None,
        email_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化通知服务
        
        Args:
            enabled: 是否启用通知
            channels: 通知渠道列表，可选值：['log', 'email', 'system']
            email_config: 邮件配置字典，包含 smtp_host, smtp_port, smtp_user, smtp_password, recipients
        """
        self.enabled = enabled
        self.channels = channels or ['log']
        self.email_config = email_config or {}
    
    def notify(
        self,
        title: str,
        message: str,
        level: str = 'info',
        execution_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        发送通知
        
        Args:
            title: 通知标题
            message: 通知消息
            level: 通知级别（info/warning/error/success）
            execution_info: 执行信息字典（可选）
        """
        if not self.enabled:
            return
        
        # 构建完整消息
        full_message = self._build_message(title, message, execution_info)
        
        # 发送到各个渠道
        if 'log' in self.channels:
            self._notify_log(title, message, level, execution_info)
        
        if 'email' in self.channels:
            self._notify_email(title, full_message, level)
        
        if 'system' in self.channels:
            self._notify_system(title, message, level)
    
    def notify_execution_result(
        self,
        execution_id: str,
        trade_date: str,
        status: str,
        errors: Optional[List[str]] = None,
        duration_seconds: Optional[float] = None
    ) -> None:
        """
        通知任务执行结果
        
        Args:
            execution_id: 执行ID
            trade_date: 交易日期
            status: 执行状态
            errors: 错误列表
            duration_seconds: 执行时长（秒）
        """
        execution_info = {
            'execution_id': execution_id,
            'trade_date': trade_date,
            'status': status,
            'errors': errors or [],
            'duration_seconds': duration_seconds
        }
        
        if status == 'SUCCESS':
            title = f"每日任务执行成功 - {trade_date}"
            message = f"任务执行成功，耗时 {duration_seconds:.2f} 秒" if duration_seconds else "任务执行成功"
            self.notify(title, message, level='success', execution_info=execution_info)
        
        elif status == 'FAILED':
            title = f"每日任务执行失败 - {trade_date}"
            error_msg = '; '.join(errors) if errors else "未知错误"
            message = f"任务执行失败: {error_msg}"
            self.notify(title, message, level='error', execution_info=execution_info)
        
        elif status == 'TIMEOUT':
            title = f"每日任务执行超时 - {trade_date}"
            message = f"任务执行超时，已超过最大执行时间"
            self.notify(title, message, level='error', execution_info=execution_info)
        
        elif status == 'DUPLICATE':
            title = f"每日任务重复执行 - {trade_date}"
            message = f"检测到重复执行，已跳过"
            self.notify(title, message, level='warning', execution_info=execution_info)
        
        else:
            title = f"每日任务执行状态更新 - {trade_date}"
            message = f"任务状态: {status}"
            self.notify(title, message, level='info', execution_info=execution_info)
    
    def _build_message(
        self,
        title: str,
        message: str,
        execution_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建完整消息"""
        lines = [title, "", message]
        
        if execution_info:
            lines.append("")
            lines.append("执行信息:")
            lines.append(f"  执行ID: {execution_info.get('execution_id', 'N/A')}")
            lines.append(f"  交易日期: {execution_info.get('trade_date', 'N/A')}")
            lines.append(f"  状态: {execution_info.get('status', 'N/A')}")
            
            if execution_info.get('duration_seconds'):
                lines.append(f"  执行时长: {execution_info.get('duration_seconds', 0):.2f} 秒")
            
            errors = execution_info.get('errors', [])
            if errors:
                lines.append("  错误:")
                for error in errors:
                    lines.append(f"    - {error}")
        
        lines.append("")
        lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)
    
    def _notify_log(
        self,
        title: str,
        message: str,
        level: str,
        execution_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """日志通知"""
        full_message = f"{title}: {message}"
        
        if level == 'error':
            logger.error(full_message)
        elif level == 'warning':
            logger.warning(full_message)
        elif level == 'success':
            logger.info(full_message)
        else:
            logger.info(full_message)
        
        if execution_info:
            logger.debug(f"执行信息: {execution_info}")
    
    def _notify_email(
        self,
        title: str,
        message: str,
        level: str
    ) -> None:
        """邮件通知"""
        if not self.email_config:
            logger.warning("邮件通知已启用但未配置SMTP")
            return
        
        smtp_host = self.email_config.get('smtp_host')
        smtp_port = self.email_config.get('smtp_port', 587)
        smtp_user = self.email_config.get('smtp_user')
        smtp_password = self.email_config.get('smtp_password')
        recipients = self.email_config.get('recipients', [])
        
        if not all([smtp_host, smtp_user, smtp_password, recipients]):
            logger.warning("邮件配置不完整，跳过邮件通知")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[DAAS Alpha] {title}"
            
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            logger.info(f"邮件通知已发送: {title}")
        
        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")
    
    def _notify_system(
        self,
        title: str,
        message: str,
        level: str
    ) -> None:
        """系统通知（macOS/Linux）"""
        system = platform.system()
        
        try:
            if system == 'Darwin':  # macOS
                import subprocess
                # 使用osascript发送macOS通知
                script = f'''
                display notification "{message}" with title "{title}"
                '''
                subprocess.run(['osascript', '-e', script], check=False)
            
            elif system == 'Linux':
                import subprocess
                # 使用notify-send发送Linux通知
                urgency = 'critical' if level == 'error' else 'normal'
                subprocess.run(
                    ['notify-send', '-u', urgency, title, message],
                    check=False
                )
            
            else:
                logger.debug(f"系统通知不支持: {system}")
        
        except Exception as e:
            logger.warning(f"发送系统通知失败: {e}")
