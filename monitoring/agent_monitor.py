"""Real-time agent monitoring and visualization."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime
from typing import Dict, List, Optional
import time


class AgentMonitor:
    """Real-time monitoring and visualization for AI agents."""
    
    # Agent personality colors
    AGENT_COLORS = {
        'Sharp': 'cyan',
        'Insider': 'yellow',
        'Degen': 'red',
        'Bookie': 'green'
    }
    
    def __init__(self):
        """Initialize agent monitor."""
        self.console = Console()
        self.agent_logs = []
        self.current_game = None
        self.agent_stats = {}
        
    def show_header(self):
        """Display welcome header."""
        header = Panel(
            "[bold magenta]🎰 BRATISLAVA BETTING SYNDICATE 🎰[/bold magenta]\n"
            "[dim]AI Agents Making Betting Decisions in Real-Time[/dim]",
            border_style="magenta"
        )
        self.console.print(header)
        self.console.print()
    
    def show_game(self, game):
        """Display current game being analyzed."""
        self.current_game = game
        
        game_panel = Panel(
            f"[bold white]{game.home_team}[/bold white] vs [bold white]{game.away_team}[/bold white]\n"
            f"[dim]Sport: {game.sport} | Bookmaker: {game.bookmaker}[/dim]\n"
            f"[green]Home: {game.home_odds}[/green] | [red]Away: {game.away_odds}[/red]",
            title="[bold]⚽ Current Game[/bold]",
            border_style="blue"
        )
        self.console.print(game_panel)
        self.console.print()
    
    def show_agent_thinking(self, agent_name: str, agent_type: str, prompt: str):
        """Display what prompt was sent to the agent."""
        color = self.AGENT_COLORS.get(agent_type, 'white')
        
        thinking_panel = Panel(
            f"[dim]{prompt[:500]}...[/dim]" if len(prompt) > 500 else f"[dim]{prompt}[/dim]",
            title=f"[{color}]💭 {agent_name} ({agent_type}) - Analyzing...[/{color}]",
            border_style=color
        )
        self.console.print(thinking_panel)
    
    def show_agent_response(self, agent_name: str, agent_type: str, response: str, decision: Optional[Dict] = None):
        """Display agent's reasoning and decision."""
        color = self.AGENT_COLORS.get(agent_type, 'white')
        
        # Format the response
        content = f"[{color}]{response}[/{color}]"
        
        # Add decision if available
        if decision:
            bet_type = decision.get('bet_type', 'PASS')
            stake = decision.get('stake', 0)
            confidence = decision.get('confidence', 0)
            
            if bet_type != 'PASS':
                content += f"\n\n[bold green]✓ DECISION: {bet_type}[/bold green]"
                content += f"\n[yellow]Stake: ${stake:.2f}[/yellow]"
                content += f"\n[cyan]Confidence: {confidence:.1%}[/cyan]"
            else:
                content += f"\n\n[bold red]✗ DECISION: PASS[/bold red]"
                content += f"\n[dim]Confidence: {confidence:.1%}[/dim]"
        
        response_panel = Panel(
            content,
            title=f"[{color}]🤖 {agent_name} ({agent_type}) - Response[/{color}]",
            border_style=color
        )
        self.console.print(response_panel)
        self.console.print()
    
    def show_betting_slip(self, bets: List[Dict]):
        """Display all bets placed for current game."""
        if not bets:
            self.console.print("[dim]No bets placed on this game.[/dim]\n")
            return
        
        table = Table(title="📋 Betting Slip", border_style="yellow")
        table.add_column("Agent", style="cyan")
        table.add_column("Bet Type", style="white")
        table.add_column("Stake", style="yellow", justify="right")
        table.add_column("Odds", style="green", justify="right")
        table.add_column("Confidence", style="magenta", justify="right")
        
        total_stake = 0
        for bet in bets:
            table.add_row(
                bet['agent'],
                bet['bet_type'],
                f"${bet['stake']:.2f}",
                f"{bet['odds']:.2f}",
                f"{bet.get('confidence', 0):.1%}"
            )
            total_stake += bet['stake']
        
        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            f"[bold]${total_stake:.2f}[/bold]",
            "",
            "",
            style="bold"
        )
        
        self.console.print(table)
        self.console.print()
    
    def show_agent_stats(self, stats: Dict):
        """Display agent statistics."""
        table = Table(title="📊 Agent Statistics", border_style="cyan")
        table.add_column("Agent", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Bankroll", style="yellow", justify="right")
        table.add_column("Bets", justify="right")
        table.add_column("Win Rate", style="green", justify="right")
        table.add_column("ROI", style="magenta", justify="right")
        
        for agent_name, agent_stats in stats.items():
            agent_type = agent_stats.get('type', 'Unknown')
            bankroll = agent_stats.get('bankroll', 0)
            total_bets = agent_stats.get('total_bets', 0)
            wins = agent_stats.get('wins', 0)
            win_rate = wins / total_bets if total_bets > 0 else 0
            roi = agent_stats.get('roi', 0)
            
            color = self.AGENT_COLORS.get(agent_type, 'white')
            
            table.add_row(
                f"[{color}]{agent_name}[/{color}]",
                agent_type,
                f"${bankroll:.2f}",
                str(total_bets),
                f"{win_rate:.1%}",
                f"{roi:+.1%}"
            )
        
        self.console.print(table)
        self.console.print()
    
    def show_separator(self):
        """Show a visual separator."""
        self.console.print("─" * 80, style="dim")
        self.console.print()
    
    def show_summary(self, total_games: int, total_bets: int, total_stake: float):
        """Show simulation summary."""
        summary = Panel(
            f"[bold white]Games Analyzed: {total_games}[/bold white]\n"
            f"[bold yellow]Total Bets Placed: {total_bets}[/bold yellow]\n"
            f"[bold green]Total Stake: ${total_stake:.2f}[/bold green]",
            title="[bold magenta]📈 Simulation Summary[/bold magenta]",
            border_style="magenta"
        )
        self.console.print(summary)
    
    def log_event(self, event_type: str, message: str):
        """Log an event with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.print(f"[dim]{timestamp}[/dim] [{event_type}] {message}")
    
    def show_error(self, error_message: str):
        """Display an error message."""
        self.console.print(f"[bold red]❌ ERROR:[/bold red] {error_message}")
        self.console.print()
    
    def show_warning(self, warning_message: str):
        """Display a warning message."""
        self.console.print(f"[bold yellow]⚠️  WARNING:[/bold yellow] {warning_message}")
        self.console.print()
    
    def show_success(self, success_message: str):
        """Display a success message."""
        self.console.print(f"[bold green]✓ SUCCESS:[/bold green] {success_message}")
        self.console.print()


# Example usage
if __name__ == "__main__":
    monitor = AgentMonitor()
    
    # Show header
    monitor.show_header()
    
    # Simulate a game
    from agents.base_agent import Game
    
    game = Game(
        id="test_1",
        home_team="Manchester United",
        away_team="Liverpool",
        sport="soccer",
        commence_time="2025-11-24T18:00:00",
        bookmaker="nike_sk",
        home_odds=2.10,
        away_odds=3.50
    )
    
    monitor.show_game(game)
    
    # Simulate agent thinking
    monitor.show_agent_thinking(
        "Sharp Sam",
        "Sharp",
        "Analyze this game using advanced statistics and Kelly Criterion..."
    )
    
    time.sleep(1)
    
    # Simulate agent response
    monitor.show_agent_response(
        "Sharp Sam",
        "Sharp",
        "Based on my analysis, Manchester United has a 52% implied probability of winning. "
        "The current odds of 2.10 provide a 5.2% edge. Kelly Criterion suggests a 3.1% stake.",
        decision={
            'bet_type': 'HOME',
            'stake': 310.00,
            'confidence': 0.52,
            'odds': 2.10
        }
    )
    
    # Show betting slip
    monitor.show_betting_slip([
        {
            'agent': 'Sharp Sam',
            'bet_type': 'HOME',
            'stake': 310.00,
            'odds': 2.10,
            'confidence': 0.52
        },
        {
            'agent': 'Degen Dave',
            'bet_type': 'HOME',
            'stake': 500.00,
            'odds': 2.10,
            'confidence': 0.75
        }
    ])
    
    # Show stats
    monitor.show_agent_stats({
        'Sharp Sam': {
            'type': 'Sharp',
            'bankroll': 10500,
            'total_bets': 15,
            'wins': 9,
            'roi': 0.08
        },
        'Degen Dave': {
            'type': 'Degen',
            'bankroll': 8500,
            'total_bets': 25,
            'wins': 12,
            'roi': -0.15
        }
    })
