"""Email notifications for simulation results."""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any, Optional
from config.settings import settings
from monitoring.logger import logger


class EmailSender:
    """Send email notifications for simulation results."""
    
    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = 587,
        sender_email: str = None,
        sender_password: str = None
    ):
        """Initialize email sender.
        
        Args:
            smtp_server: SMTP server (default from env)
            smtp_port: SMTP port (default 587)
            sender_email: Sender email (default from env)
            sender_password: Sender password (default from env)
        """
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port
        self.sender_email = sender_email or os.getenv('SENDER_EMAIL')
        self.sender_password = sender_password or os.getenv('SENDER_PASSWORD')
        self.enabled = self.sender_email and self.sender_password
    
    def send_simulation_report(
        self,
        recipient_email: str,
        simulation_id: str,
        sport: str,
        num_games: int,
        predictions: List[Dict[str, Any]],
        total_wagered: float = 0
    ) -> bool:
        """Send simulation analysis report via email.
        
        Args:
            recipient_email: Email recipient
            simulation_id: Simulation ID
            sport: Sport analyzed
            num_games: Number of games analyzed
            predictions: List of predictions
            total_wagered: Total amount wagered
        
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.warning("Email not configured - skipping")
            return False
        
        try:
            subject = f"🎰 Bratislava Betting Syndicate - {sport.upper()} Analysis"
            
            html_body = self._generate_html_report(
                simulation_id, sport, num_games, predictions, total_wagered
            )
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = recipient_email
            
            # Attach HTML
            msg.attach(MIMEText(html_body, "html"))
            
            # Send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, msg.as_string())
            
            logger.info(f"Email sent to {recipient_email}", simulation_id=simulation_id)
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _generate_html_report(
        self,
        simulation_id: str,
        sport: str,
        num_games: int,
        predictions: List[Dict[str, Any]],
        total_wagered: float
    ) -> str:
        """Generate HTML report."""
        
        predictions_html = ""
        for i, pred in enumerate(predictions[:20], 1):  # Show top 20
            reasoning = pred.get('reasoning', 'No reasoning provided')
            
            predictions_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>{i}. {pred.get('game', 'N/A')}</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong style="color: #2ecc71;">{pred.get('bet', 'N/A')}</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">€{pred.get('stake', 0):.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{pred.get('confidence', 0) * 100:.0f}%</td>
            </tr>
            <tr>
                <td colspan="4" style="padding: 10px; border-bottom: 1px solid #eee; background-color: #fafafa; font-size: 13px; color: #555; line-height: 1.5; word-wrap: break-word;">
                    💭 {reasoning}
                </td>
            </tr>
            """
        
        html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
                    .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    h1 {{ color: #1a1a1a; border-bottom: 3px solid #2ecc71; padding-bottom: 10px; }}
                    h2 {{ color: #333; margin-top: 20px; }}
                    .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0; }}
                    .stat-box {{ background-color: #f9f9f9; padding: 15px; border-left: 4px solid #2ecc71; border-radius: 4px; }}
                    .stat-value {{ font-size: 24px; font-weight: bold; color: #2ecc71; }}
                    .stat-label {{ color: #666; font-size: 12px; text-transform: uppercase; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                    th {{ background-color: #2ecc71; color: white; padding: 12px; text-align: left; }}
                    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 12px; }}
                    .pending {{ background-color: #fff3cd; padding: 15px; border-radius: 4px; margin: 15px 0; border-left: 4px solid #ffc107; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎰 Bratislava Betting Syndicate Analysis</h1>
                    
                    <div class="pending">
                        <strong>⏳ Results Pending</strong><br>
                        Predictions have been collected and stored. Real match results will be fetched end-of-day or next day for performance evaluation.
                    </div>
                    
                    <h2>Simulation Summary</h2>
                    <div class="stats">
                        <div class="stat-box">
                            <div class="stat-label">Sport</div>
                            <div class="stat-value">{sport.upper()}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Games Analyzed</div>
                            <div class="stat-value">{num_games}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Predictions Made</div>
                            <div class="stat-value">{len(predictions)}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-label">Total Wagered</div>
                            <div class="stat-value">€{total_wagered:.2f}</div>
                        </div>
                    </div>
                    
                    <h2>Predictions ({len(predictions)} total)</h2>
                    <table>
                        <tr>
                            <th>Game</th>
                            <th>Pick</th>
                            <th>Stake</th>
                            <th>Confidence</th>
                        </tr>
                        {predictions_html}
                    </table>
                    
                    <div class="footer">
                        <strong>Simulation ID:</strong> {simulation_id}<br>
                        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
                        <br>
                        This analysis was generated by the Bratislava Betting Syndicate multi-agent system.
                    </div>
                </div>
            </body>
        </html>
        """
        
        return html


# Test function
if __name__ == "__main__":
    sender = EmailSender()
    
    if not sender.enabled:
        print("❌ Email not configured. Set SENDER_EMAIL and SENDER_PASSWORD env vars")
        print("\nExample:")
        print("  export SENDER_EMAIL='your-email@gmail.com'")
        print("  export SENDER_PASSWORD='your-app-password'")
    else:
        print("✅ Email configured and ready")
