"""PDF report generation for betting syndicate results."""

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from typing import Dict, Any, List
from datetime import datetime
import os


def generate_roi_report(
    results: Dict[str, Any],
    output_path: str = "syndicate_report.pdf"
) -> str:
    """Generate a comprehensive PDF ROI report.

    Args:
        results: Simulation results dictionary
        output_path: Path to save PDF

    Returns:
        Path to generated PDF
    """
    # Create PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )

    # Container for PDF elements
    story = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2ecc71'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#3498db'),
        spaceAfter=12,
        spaceBefore=12
    )

    # Title
    story.append(Paragraph("🎰 BRATISLAVA BETTING SYNDICATE", title_style))
    story.append(Paragraph("ROI Performance Report", styles['Heading2']))
    story.append(Spacer(1, 0.2 * inch))

    # Report metadata
    metadata = [
        ["Report Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Simulation Period:", f"{results['stats']['total_bets']} games"],
        ["", ""]
    ]
    metadata_table = Table(metadata, colWidths=[2 * inch, 4 * inch])
    metadata_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
    ]))
    story.append(metadata_table)
    story.append(Spacer(1, 0.3 * inch))

    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))

    stats = results['stats']
    roi_color = colors.green if stats['roi'] > 0 else colors.red

    summary_data = [
        ["Metric", "Value"],
        ["Starting Bankroll", f"€{stats['initial_bankroll']:,.2f}"],
        ["Final Bankroll", f"€{stats['current_bankroll']:,.2f}"],
        ["Profit/Loss", f"€{stats['profit_loss']:+,.2f}"],
        ["ROI", f"{stats['roi']:+.2f}%"],
        ["Total Bets", str(stats['total_bets'])],
        ["Win Rate", f"{stats['win_rate']:.1f}%"],
        ["Total Wagered", f"€{stats['total_wagered']:,.2f}"],
        ["Avg Bet Size", f"€{stats['average_bet_size']:.2f}"]
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 12),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('TEXTCOLOR', (1, 4), (1, 4), roi_color),
        ('FONT', (1, 4), (1, 4), 'Helvetica-Bold', 12),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.4 * inch))

    # Agent Performance
    story.append(Paragraph("Agent Performance Rankings", heading_style))

    agent_stats = sorted(results['agent_stats'], key=lambda x: x['roi'], reverse=True)

    agent_data = [["Rank", "Agent", "Type", "ROI", "Win Rate", "Profit/Loss"]]
    for i, agent in enumerate(agent_stats, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else ""
        agent_data.append([
            f"{emoji}{i}",
            agent['name'],
            agent['type'].upper(),
            f"{agent['roi']:+.2f}%",
            f"{agent['win_rate']:.1f}%",
            f"€{agent['profit_loss']:+.2f}"
        ])

    agent_table = Table(agent_data, colWidths=[0.6 * inch, 1.5 * inch, 1 * inch, 1 * inch, 1 * inch, 1.3 * inch])
    agent_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(agent_table)
    story.append(PageBreak())

    # Strategy Analysis
    story.append(Paragraph("Strategy Analysis by Agent Type", heading_style))

    type_summary = {}
    for agent in agent_stats:
        agent_type = agent['type']
        if agent_type not in type_summary:
            type_summary[agent_type] = {
                'count': 0,
                'total_roi': 0,
                'total_win_rate': 0
            }
        type_summary[agent_type]['count'] += 1
        type_summary[agent_type]['total_roi'] += agent['roi']
        type_summary[agent_type]['total_win_rate'] += agent['win_rate']

    type_data = [["Agent Type", "Agents", "Avg ROI", "Avg Win Rate"]]
    for agent_type, data in type_summary.items():
        count = data['count']
        type_data.append([
            agent_type.upper(),
            str(count),
            f"{data['total_roi'] / count:+.2f}%",
            f"{data['total_win_rate'] / count:.1f}%"
        ])

    type_table = Table(type_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    type_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(type_table)
    story.append(Spacer(1, 0.3 * inch))

    # Key Insights
    story.append(Paragraph("Key Insights", heading_style))

    insights = []

    # Best performer
    best_agent = agent_stats[0]
    insights.append(f"• Top performer: {best_agent['name']} ({best_agent['type']}) with {best_agent['roi']:+.2f}% ROI")

    # Worst performer
    worst_agent = agent_stats[-1]
    insights.append(f"• Worst performer: {worst_agent['name']} ({worst_agent['type']}) with {worst_agent['roi']:+.2f}% ROI")

    # Overall strategy
    if stats['roi'] > 0:
        insights.append(f"• Overall strategy: PROFITABLE (+{stats['roi']:.2f}% ROI)")
    else:
        insights.append(f"• Overall strategy: UNPROFITABLE ({stats['roi']:.2f}% ROI)")

    # Win rate analysis
    if stats['win_rate'] > 52.4:
        insights.append(f"• Win rate of {stats['win_rate']:.1f}% beats breakeven (52.4% for -110 odds)")
    else:
        insights.append(f"• Win rate of {stats['win_rate']:.1f}% needs improvement (breakeven: 52.4%)")

    for insight in insights:
        story.append(Paragraph(insight, styles['Normal']))
        story.append(Spacer(1, 0.1 * inch))

    story.append(Spacer(1, 0.3 * inch))

    # Recommendations
    story.append(Paragraph("Recommendations", heading_style))

    recommendations = [
        "• Focus on agent types with positive ROI",
        "• Reduce stake sizes for underperforming agents",
        "• Increase Kelly fraction if win rate > 55%",
        "• Consider adding more sharp agents if they outperform",
        "• Track closing line value (CLV) for sharps"
    ]

    for rec in recommendations:
        story.append(Paragraph(rec, styles['Normal']))
        story.append(Spacer(1, 0.1 * inch))

    # Footer
    story.append(Spacer(1, 0.5 * inch))
    footer_text = """
    <para align=center>
    <font size=8 color="#95a5a6">
    Generated by Bratislava Betting Syndicate | Powered by LangGraph + Claude<br/>
    For educational purposes only. Gamble responsibly.
    </font>
    </para>
    """
    story.append(Paragraph(footer_text, styles['Normal']))

    # Build PDF
    doc.build(story)

    print(f"✅ PDF report generated: {output_path}")
    return output_path


def generate_quick_summary(results: Dict[str, Any]) -> str:
    """Generate a quick text summary of results.

    Args:
        results: Simulation results

    Returns:
        Formatted text summary
    """
    stats = results['stats']
    agent_stats = sorted(results['agent_stats'], key=lambda x: x['roi'], reverse=True)

    summary = f"""
╔═══════════════════════════════════════════════════════════╗
║   BRATISLAVA BETTING SYNDICATE - SUMMARY REPORT          ║
╚═══════════════════════════════════════════════════════════╝

💰 FINANCIAL PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Starting Bankroll:    €{stats['initial_bankroll']:,.2f}
Final Bankroll:       €{stats['current_bankroll']:,.2f}
Profit/Loss:          €{stats['profit_loss']:+,.2f}
ROI:                  {stats['roi']:+.2f}%

📊 BETTING STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Bets:           {stats['total_bets']}
Wins:                 {stats['wins']}
Losses:               {stats['losses']}
Win Rate:             {stats['win_rate']:.1f}%
Total Wagered:        €{stats['total_wagered']:,.2f}
Average Bet Size:     €{stats['average_bet_size']:.2f}

🏆 TOP 3 AGENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    for i, agent in enumerate(agent_stats[:3], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        summary += f"{emoji} {agent['name']} ({agent['type']}): {agent['roi']:+.2f}% ROI\n"

    summary += "\n"
    return summary
