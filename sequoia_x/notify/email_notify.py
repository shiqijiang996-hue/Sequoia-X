"""
邮件推送模块（QQ邮箱 SMTP）。

接口设计参照 sequoia_x/notify/feishu.py 的 FeishuNotifier，
保持 send(symbols, strategy_name, webhook_key=None) 签名一致，
便于在 main.py 中与 FeishuNotifier 并列调用，互不影响。

环境变量（写在 .env 或 GitHub Actions Secrets 中）：
  EMAIL_SENDER    发件邮箱地址，如 123456@qq.com
  EMAIL_PASSWORD  邮箱"授权码"（不是登录密码，QQ邮箱设置里获取）
  EMAIL_RECEIVER  收件邮箱地址，可与发件邮箱相同
  EMAIL_ENABLED   是否启用邮件推送，"true"/"false"，默认 true（只要配了SENDER就发）
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from datetime import date

from sequoia_x.core.logger import get_logger

logger = get_logger(__name__)

QQ_SMTP_HOST = "smtp.qq.com"
QQ_SMTP_PORT = 465  # SSL端口


class EmailNotifier:
    """QQ邮箱 SMTP 推送器，接口与 FeishuNotifier 保持一致。"""

    def __init__(self, settings=None):
        # settings 参数保留是为了和 FeishuNotifier(settings) 调用方式对齐，
        # 当前邮件推送直接读环境变量，不依赖 settings 对象。
        self.sender = os.getenv("EMAIL_SENDER")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.receiver = os.getenv("EMAIL_RECEIVER", self.sender)
        self.enabled = os.getenv("EMAIL_ENABLED", "true").lower() == "true"

        if self.enabled and (not self.sender or not self.password):
            logger.warning("EMAIL_SENDER 或 EMAIL_PASSWORD 未配置，邮件推送将被跳过")
            self.enabled = False

    def send(self, symbols: list[str], strategy_name: str, webhook_key: str | None = None) -> bool:
        """
        发送选股结果邮件。

        Args:
            symbols: 选出的股票代码/名称列表
            strategy_name: 策略名称，如 "TurtleTrade"
            webhook_key: 兼容 FeishuNotifier 接口保留，邮件推送不使用此参数

        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            return False

        if not symbols:
            return False

        today = date.today().isoformat()
        subject = f"【Sequoia-X】{today} {strategy_name} 选出 {len(symbols)} 只"

        lines = [f"策略：{strategy_name}", f"日期：{today}", f"共选出 {len(symbols)} 只股票", ""]
        for s in symbols:
            lines.append(f"  - {s}")
        lines.append("")
        lines.append("仅供参考，不构成投资建议。")
        content = "\n".join(lines)

        return self._send_mail(subject, content)

    def _send_mail(self, subject: str, content: str) -> bool:
        msg = MIMEText(content, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr(("Sequoia-X选股助手", self.sender))
        msg["To"] = formataddr(("我", self.receiver))

        try:
            with smtplib.SMTP_SSL(QQ_SMTP_HOST, QQ_SMTP_PORT, timeout=15) as server:
                server.login(self.sender, self.password)
                server.sendmail(self.sender, [self.receiver], msg.as_string())
            logger.info(f"邮件推送成功：{subject}")
            return True
        except Exception as e:
            logger.error(f"邮件推送失败：{e}")
            return False
