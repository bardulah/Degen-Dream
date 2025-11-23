"""Visualization utilities for betting syndicate data."""

import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any
import pandas as pd


def create_roi_chart(performance_data: List[Dict[str, Any]]) -> go.Figure:
    """Create ROI over time chart.

    Args:
        performance_data: List of performance snapshots

    Returns:
        Plotly figure
    """
    df = pd.DataFrame(performance_data)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['roi'],
        mode='lines+markers',
        name='ROI',
        line=dict(color='#2ecc71', width=3),
        marker=dict(size=6)
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        title="📈 ROI Over Time",
        xaxis_title="Games Played",
        yaxis_title="ROI (%)",
        template="plotly_dark",
        hovermode='x unified'
    )

    return fig


def create_bankroll_chart(performance_data: List[Dict[str, Any]]) -> go.Figure:
    """Create bankroll progression chart.

    Args:
        performance_data: List of performance snapshots

    Returns:
        Plotly figure
    """
    df = pd.DataFrame(performance_data)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['bankroll'],
        mode='lines',
        name='Bankroll',
        fill='tozeroy',
        line=dict(color='#3498db', width=2)
    ))

    fig.update_layout(
        title="💰 Bankroll Progression",
        xaxis_title="Games Played",
        yaxis_title="Bankroll (€)",
        template="plotly_dark",
        hovermode='x unified'
    )

    return fig


def create_agent_comparison(agent_stats: List[Dict[str, Any]]) -> go.Figure:
    """Create agent performance comparison chart.

    Args:
        agent_stats: List of agent statistics

    Returns:
        Plotly figure
    """
    df = pd.DataFrame(agent_stats)
    df = df.sort_values('roi', ascending=False)

    # Color code by agent type
    colors = {
        'sharp': '#2ecc71',
        'insider': '#9b59b6',
        'degen': '#e74c3c',
        'bookie': '#f39c12'
    }
    df['color'] = df['type'].map(colors)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df['name'],
        y=df['roi'],
        marker_color=df['color'],
        text=df['roi'].round(1),
        textposition='outside',
        texttemplate='%{text}%'
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="white")

    fig.update_layout(
        title="🏆 Agent ROI Comparison",
        xaxis_title="Agent",
        yaxis_title="ROI (%)",
        template="plotly_dark",
        showlegend=False
    )

    return fig


def create_win_rate_chart(agent_stats: List[Dict[str, Any]]) -> go.Figure:
    """Create win rate comparison chart.

    Args:
        agent_stats: List of agent statistics

    Returns:
        Plotly figure
    """
    df = pd.DataFrame(agent_stats)
    df = df.sort_values('win_rate', ascending=False)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df['name'],
        y=df['win_rate'],
        marker_color='#3498db',
        text=df['win_rate'].round(1),
        textposition='outside',
        texttemplate='%{text}%'
    ))

    fig.update_layout(
        title="🎯 Win Rate by Agent",
        xaxis_title="Agent",
        yaxis_title="Win Rate (%)",
        template="plotly_dark"
    )

    return fig


def create_bet_distribution(results: List[Dict[str, Any]]) -> go.Figure:
    """Create bet type distribution chart.

    Args:
        results: List of bet results

    Returns:
        Plotly figure
    """
    df = pd.DataFrame(results)

    wins = df[df['won'] == True].shape[0]
    losses = df[df['won'] == False].shape[0]

    fig = go.Figure(data=[go.Pie(
        labels=['Wins', 'Losses'],
        values=[wins, losses],
        marker_colors=['#2ecc71', '#e74c3c'],
        hole=0.4
    )])

    fig.update_layout(
        title="🎲 Win/Loss Distribution",
        template="plotly_dark"
    )

    return fig
