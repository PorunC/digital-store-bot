"""Email notification implementation."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Email notification service."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.smtp_server = self.config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.username = self.config.get("username")
        self.password = self.config.get("password")
        self.from_email = self.config.get("from_email", self.username)
        self.from_name = self.config.get("from_name", "Digital Store Bot")
        
        self.enabled = bool(self.username and self.password)
        
        if not self.enabled:
            logger.warning("Email notifications disabled - missing SMTP configuration")
    
    async def send_notification(self, notification_data: Dict[str, Any]) -> bool:
        """Send notification via email."""
        if not self.enabled:
            logger.warning("Email notifications are disabled")
            return False
        
        try:
            notification_type = notification_data.get("type")
            user = notification_data.get("user")
            template_data = notification_data.get("template_data", {})
            
            # Skip if user has no email
            if not user or not hasattr(user, 'profile') or not user.profile.email:
                logger.info("User has no email address, skipping email notification")
                return True  # Not an error, just not applicable
            
            # Get email content
            subject, html_content, text_content = self._get_email_template(
                notification_type, template_data
            )
            
            if not subject or not (html_content or text_content):
                logger.error(f"No email template found for notification type: {notification_type}")
                return False
            
            # Send email
            success = await self._send_email(
                to_email=user.profile.email,
                to_name=user.profile.first_name,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
    
    def _get_email_template(
        self,
        notification_type,
        template_data: Dict[str, Any]
    ) -> tuple[str, str, str]:
        """Get email template for notification type."""
        templates = {
            "payment_success": self._payment_success_email_template,
            "payment_failed": self._payment_failed_email_template,
            "order_created": self._order_created_email_template,
            "subscription_expiring": self._subscription_expiring_email_template,
            "trial_started": self._trial_started_email_template,
        }
        
        template_func = templates.get(str(notification_type).replace("NotificationType.", ""))
        if template_func:
            return template_func(template_data)
        
        return "", "", ""
    
    def _payment_success_email_template(self, data: Dict[str, Any]) -> tuple[str, str, str]:
        """Payment success email template."""
        subject = f"Payment Successful - Order #{data.get('order_id', 'N/A')}"
        
        html_content = f"""
        <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #28a745;">🎉 Payment Successful!</h2>
                    
                    <p>Hi {data.get('user_name', 'User')},</p>
                    
                    <p>Great news! Your payment has been processed successfully.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Order Details:</h3>
                        <p><strong>Product:</strong> {data.get('product_name', 'N/A')}</p>
                        <p><strong>Amount:</strong> {data.get('amount', 'N/A')} {data.get('currency', '')}</p>
                        <p><strong>Order ID:</strong> {data.get('order_id', 'N/A')}</p>
                        <p><strong>Completed:</strong> {data.get('completion_date', 'Just now')}</p>
                    </div>
                    
                    <p>🎁 Your subscription has been activated! You now have access to all premium features.</p>
                    
                    <p>Thank you for your purchase!</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #6c757d; font-size: 12px;">
                        This is an automated message from Digital Store Bot.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Payment Successful!
        
        Hi {data.get('user_name', 'User')},
        
        Great news! Your payment has been processed successfully.
        
        Order Details:
        - Product: {data.get('product_name', 'N/A')}
        - Amount: {data.get('amount', 'N/A')} {data.get('currency', '')}
        - Order ID: {data.get('order_id', 'N/A')}
        - Completed: {data.get('completion_date', 'Just now')}
        
        Your subscription has been activated! You now have access to all premium features.
        
        Thank you for your purchase!
        
        ---
        This is an automated message from Digital Store Bot.
        """
        
        return subject, html_content, text_content
    
    def _payment_failed_email_template(self, data: Dict[str, Any]) -> tuple[str, str, str]:
        """Payment failed email template."""
        subject = f"Payment Failed - Order #{data.get('order_id', 'N/A')}"
        
        html_content = f"""
        <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #dc3545;">❌ Payment Failed</h2>
                    
                    <p>Hi {data.get('user_name', 'User')},</p>
                    
                    <p>Unfortunately, we were unable to process your payment.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Order Details:</h3>
                        <p><strong>Product:</strong> {data.get('product_name', 'N/A')}</p>
                        <p><strong>Amount:</strong> {data.get('amount', 'N/A')} {data.get('currency', '')}</p>
                        <p><strong>Order ID:</strong> {data.get('order_id', 'N/A')}</p>
                        <p><strong>Error:</strong> {data.get('error_message', 'Unknown error')}</p>
                    </div>
                    
                    <p>📞 Need help? Please contact our support team.</p>
                    <p>🔄 You can try ordering again anytime.</p>
                    
                    <p>We're here to help!</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #6c757d; font-size: 12px;">
                        This is an automated message from Digital Store Bot.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Payment Failed
        
        Hi {data.get('user_name', 'User')},
        
        Unfortunately, we were unable to process your payment.
        
        Order Details:
        - Product: {data.get('product_name', 'N/A')}
        - Amount: {data.get('amount', 'N/A')} {data.get('currency', '')}
        - Order ID: {data.get('order_id', 'N/A')}
        - Error: {data.get('error_message', 'Unknown error')}
        
        Need help? Please contact our support team.
        You can try ordering again anytime.
        
        We're here to help!
        
        ---
        This is an automated message from Digital Store Bot.
        """
        
        return subject, html_content, text_content
    
    def _order_created_email_template(self, data: Dict[str, Any]) -> tuple[str, str, str]:
        """Order created email template."""
        subject = f"Order Created - #{data.get('order_id', 'N/A')}"
        
        html_content = f"""
        <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #007bff;">🛍️ Order Created</h2>
                    
                    <p>Hi {data.get('user_name', 'User')},</p>
                    
                    <p>Your order has been created and is waiting for payment.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Order Details:</h3>
                        <p><strong>Product:</strong> {data.get('product_name', 'N/A')}</p>
                        <p><strong>Amount:</strong> {data.get('amount', 'N/A')} {data.get('currency', '')}</p>
                        <p><strong>Order ID:</strong> {data.get('order_id', 'N/A')}</p>
                        {"<p><strong>Expires:</strong> " + data.get('expires_at', 'N/A') + "</p>" if data.get('expires_at') else ""}
                    </div>
                    
                    {"<p>💳 Please complete your payment to activate your subscription.</p>" if data.get('payment_url') else "<p>⏳ We're processing your payment...</p>"}
                    
                    <p>Thank you for your order!</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #6c757d; font-size: 12px;">
                        This is an automated message from Digital Store Bot.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Order Created
        
        Hi {data.get('user_name', 'User')},
        
        Your order has been created and is waiting for payment.
        
        Order Details:
        - Product: {data.get('product_name', 'N/A')}
        - Amount: {data.get('amount', 'N/A')} {data.get('currency', '')}
        - Order ID: {data.get('order_id', 'N/A')}
        {f"- Expires: {data.get('expires_at', 'N/A')}" if data.get('expires_at') else ""}
        
        {"Please complete your payment to activate your subscription." if data.get('payment_url') else "We're processing your payment..."}
        
        Thank you for your order!
        
        ---
        This is an automated message from Digital Store Bot.
        """
        
        return subject, html_content, text_content
    
    def _subscription_expiring_email_template(self, data: Dict[str, Any]) -> tuple[str, str, str]:
        """Subscription expiring email template."""
        subject = f"Subscription Expiring Soon - {data.get('days_remaining', 'N/A')} Days Left"
        
        html_content = f"""
        <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #ffc107;">⏰ Subscription Expiring Soon</h2>
                    
                    <p>Hi {data.get('user_name', 'User')},</p>
                    
                    <p>Your {data.get('subscription_type', 'subscription')} expires in <strong>{data.get('days_remaining', 'N/A')} day(s)</strong>.</p>
                    
                    <div style="background-color: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                        <p><strong>Expires on:</strong> {data.get('expires_date', 'N/A')}</p>
                    </div>
                    
                    <p>💡 Don't lose access to premium features! Renew your subscription today.</p>
                    
                    <p>🎁 Special offers may be available!</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #6c757d; font-size: 12px;">
                        This is an automated message from Digital Store Bot.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Subscription Expiring Soon
        
        Hi {data.get('user_name', 'User')},
        
        Your {data.get('subscription_type', 'subscription')} expires in {data.get('days_remaining', 'N/A')} day(s).
        
        Expires on: {data.get('expires_date', 'N/A')}
        
        Don't lose access to premium features! Renew your subscription today.
        
        Special offers may be available!
        
        ---
        This is an automated message from Digital Store Bot.
        """
        
        return subject, html_content, text_content
    
    def _trial_started_email_template(self, data: Dict[str, Any]) -> tuple[str, str, str]:
        """Trial started email template."""
        subject = f"Free Trial Started - {data.get('trial_days', 'N/A')} Days"
        
        html_content = f"""
        <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #28a745;">🎁 Free Trial Started!</h2>
                    
                    <p>Welcome {data.get('user_name', 'User')}!</p>
                    
                    <p>🌟 Your <strong>{data.get('trial_days', 'N/A')}-day free trial</strong> is now active!</p>
                    
                    <div style="background-color: #d4edda; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                        <p><strong>Expires on:</strong> {data.get('expires_date', 'N/A')}</p>
                    </div>
                    
                    <p>✨ Enjoy full access to all premium features:</p>
                    <ul>
                        <li>Unlimited usage</li>
                        <li>Priority support</li>
                        <li>Advanced features</li>
                    </ul>
                    
                    <p>💡 Consider upgrading before your trial ends to continue enjoying these benefits!</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #6c757d; font-size: 12px;">
                        This is an automated message from Digital Store Bot.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Free Trial Started!
        
        Welcome {data.get('user_name', 'User')}!
        
        Your {data.get('trial_days', 'N/A')}-day free trial is now active!
        
        Expires on: {data.get('expires_date', 'N/A')}
        
        Enjoy full access to all premium features:
        - Unlimited usage
        - Priority support
        - Advanced features
        
        Consider upgrading before your trial ends to continue enjoying these benefits!
        
        ---
        This is an automated message from Digital Store Bot.
        """
        
        return subject, html_content, text_content
    
    async def _send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str = "",
        text_content: str = ""
    ) -> bool:
        """Send email to recipient."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>"
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML content
            if html_content:
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_bulk_notifications(
        self,
        notifications: List[Dict[str, Any]]
    ) -> List[bool]:
        """Send multiple email notifications in batch."""
        results = []
        
        for notification in notifications:
            try:
                result = await self.send_notification(notification)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in bulk email notification: {e}")
                results.append(False)
        
        return results