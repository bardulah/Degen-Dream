# 🎰 Bratislava Betting Syndicate - Setup Guide

Complete setup guide for running the multi-agent betting simulation.

## Prerequisites

- Python 3.9+
- Anthropic API key (Claude Sonnet 4.5)
- TheOddsAPI key (optional, for live data)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/Degen-Dream.git
cd Degen-Dream
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ODDS_API_KEY=your_odds_api_key_here  # Optional
```

### 5. Run Simulation

#### Command Line

```bash
python main.py
```

Options:
```bash
python main.py --games 200 --sport basketball_nba --live
```

#### Streamlit GUI

```bash
streamlit run gui/streamlit_app.py
```

Then open http://localhost:8501 in your browser.

## Configuration

### Agent Settings

Edit `config/settings.py` to customize:

- Number of each agent type (sharps, insiders, degens, bookies)
- Starting bankroll
- Kelly fraction (risk tolerance)
- Simulation parameters

### Agent Personalities

Modify agent prompts in `config/settings.py` under `AGENT_PROMPTS`.

Example:
```python
AGENT_PROMPTS = {
    "Viktor": "You're Viktor, a sharp bettor who only cares about expected value...",
    # ... customize as needed
}
```

## Usage

### Command Line Interface

```bash
# Run 100 games with sample data
python main.py

# Run 200 games with live NBA data
python main.py --games 200 --sport basketball_nba --live

# Available sports:
# - soccer_epl
# - basketball_nba
# - americanfootball_nfl
# - icehockey_nhl
# - soccer_spain_la_liga
# - soccer_italy_serie_a
```

### Streamlit GUI

The GUI provides:
- Interactive simulation controls
- Real-time agent debates
- Performance charts (ROI, bankroll, agent comparison)
- Agent leaderboard
- CSV and PDF export

### Python API

```python
from data.odds_api import OddsAPIClient
from simulation.graph import run_simulation

# Get games
client = OddsAPIClient()
games = client.get_odds(sport="soccer_epl")

# Run simulation
results = run_simulation(
    games=games,
    num_games=100,
    starting_bankroll=10000
)

# Access results
print(f"ROI: {results['stats']['roi']:.2f}%")
print(f"Win Rate: {results['stats']['win_rate']:.1f}%")
```

## Advanced Features

### Custom Agents

Create custom agents by extending `BaseAgent`:

```python
from agents.base_agent import BaseAgent, AgentType

class MyCustomAgent(BaseAgent):
    def __init__(self, name: str, personality_prompt: str):
        super().__init__(name, AgentType.SHARP, personality_prompt)

    def analyze_game(self, game, context):
        # Your custom logic here
        pass
```

### Kelly Criterion

Adjust risk with Kelly fraction:

```python
# Conservative (quarter-Kelly)
KELLY_FRACTION = 0.25

# Aggressive (half-Kelly)
KELLY_FRACTION = 0.50

# Full Kelly (max variance)
KELLY_FRACTION = 1.0
```

### PDF Reports

Generate PDF reports:

```python
from export.pdf_generator import generate_roi_report

results = run_simulation(...)
generate_roi_report(results, "my_report.pdf")
```

## Data Sources

### TheOddsAPI

Sign up at https://the-odds-api.com/

Free tier: 500 requests/month

Supported sports:
- Soccer (EPL, La Liga, Serie A, etc.)
- Basketball (NBA)
- American Football (NFL)
- Ice Hockey (NHL)
- Tennis, MMA, and more

### Sample Data

The system includes sample games for testing without API calls.

### Custom Data

Integrate your own data sources by extending `OddsAPIClient` or creating custom scrapers.

## Troubleshooting

### "ANTHROPIC_API_KEY is required"

Make sure you've:
1. Created a `.env` file (copy from `.env.example`)
2. Added your Anthropic API key
3. The key is valid and has credits

### "No games found"

- If using live data, check your TheOddsAPI key and quota
- Fall back to sample data with `--sample` flag
- Check internet connection

### Import Errors

Make sure virtual environment is activated and dependencies installed:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Streamlit Connection Error

Check that port 8501 is not in use:

```bash
lsof -i :8501  # Find process
kill -9 <PID>  # Kill it
```

Or use a different port:

```bash
streamlit run gui/streamlit_app.py --server.port 8502
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
black .
flake8 .
mypy .
```

### Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Deployment

### Streamlit Cloud

1. Push to GitHub
2. Connect to Streamlit Cloud
3. Add environment variables (API keys)
4. Deploy!

### Docker

```bash
docker build -t bratislava-syndicate .
docker run -p 8501:8501 bratislava-syndicate
```

### Production Considerations

- Use environment-specific `.env` files
- Set up proper logging
- Implement rate limiting
- Add authentication for Streamlit
- Set up monitoring (Sentry, etc.)
- Use production database for subscriptions

## Support

- 📧 Email: support@bratislava-syndicate.com
- 💬 Discord: https://discord.gg/bratislava
- 🐛 Issues: https://github.com/yourusername/Degen-Dream/issues

## License

MIT License - See LICENSE file for details

---

**Made with chaos in Bratislava 🇸🇰**
