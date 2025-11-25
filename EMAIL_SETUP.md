# Email Notifications Setup

Automatically send simulation reports via email after each daily run.

## Configuration

Set environment variables:

```bash
# Using Gmail with App Password
export SENDER_EMAIL="your-email@gmail.com"
export SENDER_PASSWORD="your-16-char-app-password"

# Optional: Custom SMTP server
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
```

## Gmail Setup (Recommended)

1. **Enable 2-Factor Authentication**
   - Go to https://myaccount.google.com/security
   - Enable 2-Step Verification

2. **Generate App Password**
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer"
   - Copy the 16-character password

3. **Set Environment Variables**
   ```bash
   export SENDER_EMAIL="your-email@gmail.com"
   export SENDER_PASSWORD="xxxx xxxx xxxx xxxx"  # The 16-char password
   ```

## Running with Email

```bash
# Run daily simulation - will send email report if configured
python main.py --daily --games 10

# Or scheduled daily:
python scheduler.py --time 08:00
```

## Email Report Contents

Reports include:
- Sport analyzed (EPL, NBA, etc)
- Number of games analyzed
- All predictions with:
  - Matchup
  - Consensus pick
  - Stake
  - Confidence level
- Total wagered
- Status: "Results Pending" (will be matched with real scores next day)

## Testing Email

```bash
python -c "
from notification.email_sender import EmailSender

sender = EmailSender()
if sender.enabled:
    sender.send_simulation_report(
        recipient_email='your-email@gmail.com',
        simulation_id='test-123',
        sport='soccer',
        num_games=5,
        predictions=[
            {'game': 'Chelsea vs Barcelona', 'bet': 'Chelsea', 'stake': 100, 'confidence': 85},
            {'game': 'Arsenal vs Bayern', 'bet': 'Arsenal', 'stake': 75, 'confidence': 80},
        ],
        total_wagered=175
    )
    print('✅ Test email sent')
else:
    print('❌ Email not configured')
"
```

## Other Email Providers

### Office 365 / Outlook
```bash
export SENDER_EMAIL="your-email@outlook.com"
export SENDER_PASSWORD="your-password"
export SMTP_SERVER="smtp.office365.com"
export SMTP_PORT="587"
```

### SendGrid
Requires API key setup (can extend EmailSender class)

### Mailgun
Requires API key setup (can extend EmailSender class)

## Troubleshooting

### "SMTP connection refused"
- Check SMTP_SERVER and SMTP_PORT
- Gmail: smtp.gmail.com:587
- Outlook: smtp.office365.com:587

### "Authentication failed"
- Verify SENDER_PASSWORD is correct
- For Gmail: use App Password, not account password
- Check 2-Factor Authentication is enabled

### "Module not found"
- Email requires no additional dependencies (uses built-in smtplib)

## Scheduling with Email

Combine with cron for daily runs with email:

```bash
# Run every day at 8 AM, email report to user
0 8 * * * cd /path/to/Degen-Dream && python main.py --daily --games 15
```

Or use the scheduler:
```bash
python scheduler.py --time 08:00
```

The scheduler will:
1. Fetch today's odds from Nike.sk
2. Run agent analysis
3. Send email report to registered user
4. Store bets in database for next-day result matching
