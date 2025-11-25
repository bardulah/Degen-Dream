"""PDF report generation for simulations."""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.units import inch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import io


class PDFGenerator:
    """Generate PDF reports for simulation results."""

    def __init__(self):
        self.pagesize = letter
        self.styles = getSampleStyleSheet()
        self.export_dir = Path(__file__).parent

    def generate_report(
        self,
        simulation_id: str,
        user_email: str,
        results: Dict[str, Any],
        agent_stats: List[Dict[str, Any]],
        filename: str = None
    ) -> str:
        """
        Generate PDF report for simulation.
        
        Args:
            simulation_id: Simulation ID
            user_email: User email
            results: Simulation results dict with stats
            agent_stats: List of agent statistics
            filename: Output filename (default: simulation_id.pdf)
        
        Returns:
            Path to generated PDF
        """
        if filename is None:
            filename = f"{simulation_id}.pdf"
        
        filepath = self.export_dir / filename
        
        # Create PDF
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=self.pagesize,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )
        
        # Build story
        story = []
        
        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#2ecc71"),
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("🎰 Bratislava Betting Syndicate", title_style))
        story.append(Paragraph("Simulation Report", self.styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))
        
        # Metadata
        meta_style = ParagraphStyle(
            "Meta",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.grey
        )
        story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", meta_style))
        story.append(Paragraph(f"<b>User:</b> {user_email}", meta_style))
        story.append(Paragraph(f"<b>Simulation ID:</b> {simulation_id}", meta_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # Summary stats
        story.append(Paragraph("📊 Summary Statistics", self.styles["Heading2"]))
        summary_data = [
            ["Metric", "Value"],
            ["Starting Bankroll", f"€{results['stats'].get('starting_bankroll', 0):,.2f}"],
            ["Final Bankroll", f"€{results['stats'].get('current_bankroll', 0):,.2f}"],
            ["ROI", f"{results['stats'].get('roi', 0):+.2f}%"],
            ["Win Rate", f"{results['stats'].get('win_rate', 0):.1f}%"],
            ["Total Bets", f"{results['stats'].get('total_bets', 0)}"],
            ["Total Wagered", f"€{results['stats'].get('total_wagered', 0):,.2f}"],
            ["Max Drawdown", f"{results['stats'].get('max_drawdown', 0):+.2f}%"],
            ["Duration", f"{results['stats'].get('duration_seconds', 0)}s"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2ecc71")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Agent performance
        story.append(Paragraph("🤖 Agent Performance Rankings", self.styles["Heading2"]))
        
        agent_stats_sorted = sorted(agent_stats, key=lambda x: x["roi"], reverse=True)
        agent_data = [
            ["Rank", "Agent", "Type", "ROI", "Win Rate", "Bets", "Profit/Loss"]
        ]
        
        for i, agent in enumerate(agent_stats_sorted, 1):
            agent_data.append([
                str(i),
                agent.get("name", "Unknown"),
                agent.get("type", "").capitalize(),
                f"{agent.get('roi', 0):+.1f}%",
                f"{agent.get('win_rate', 0):.1f}%",
                str(agent.get("total_bets", 0)),
                f"€{agent.get('profit_loss', 0):+,.0f}"
            ])
        
        agent_table = Table(agent_data, colWidths=[0.6*inch, 1.5*inch, 1*inch, 0.8*inch, 1*inch, 0.7*inch, 1*inch])
        agent_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ("FONTSIZE", (0, 1), (-1, -1), 9)
        ]))
        story.append(agent_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Footer
        footer_style = ParagraphStyle(
            "Footer",
            parent=self.styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
            alignment=1
        )
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(
            "This report is for educational and informational purposes only. "
            "Past performance does not guarantee future results.",
            footer_style
        ))
        
        # Build PDF
        doc.build(story)
        
        return str(filepath)

    def generate_report_bytes(
        self,
        simulation_id: str,
        user_email: str,
        results: Dict[str, Any],
        agent_stats: List[Dict[str, Any]]
    ) -> bytes:
        """Generate PDF as bytes for streaming response."""
        # Create in-memory PDF
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.pagesize,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )
        
        story = []
        
        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#2ecc71"),
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph("🎰 Bratislava Betting Syndicate", title_style))
        story.append(Paragraph("Simulation Report", self.styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))
        
        # Metadata
        meta_style = ParagraphStyle(
            "Meta",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.grey
        )
        story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", meta_style))
        story.append(Paragraph(f"<b>User:</b> {user_email}", meta_style))
        story.append(Paragraph(f"<b>Simulation ID:</b> {simulation_id}", meta_style))
        story.append(Spacer(1, 0.3 * inch))
        
        # Summary stats
        story.append(Paragraph("📊 Summary Statistics", self.styles["Heading2"]))
        summary_data = [
            ["Metric", "Value"],
            ["Starting Bankroll", f"€{results['stats'].get('starting_bankroll', 0):,.2f}"],
            ["Final Bankroll", f"€{results['stats'].get('current_bankroll', 0):,.2f}"],
            ["ROI", f"{results['stats'].get('roi', 0):+.2f}%"],
            ["Win Rate", f"{results['stats'].get('win_rate', 0):.1f}%"],
            ["Total Bets", f"{results['stats'].get('total_bets', 0)}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2ecc71")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(summary_table)
        
        # Build PDF in memory
        doc.build(story)
        
        # Get bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
