#!/usr/bin/env python3
"""
Update Results - CLI tool to fetch live scores and update bet results.

This script:
1. Checks for bets with pending results
2. Fetches live scores from ESPN API
3. Matches scores to bets and updates outcomes
4. Recalculates simulation and agent statistics

Usage:
    python update_results.py                    # Check yesterday's games
    python update_results.py --date 20241126   # Check specific date
    python update_results.py --simulation-id <uuid>  # Update specific simulation
    python update_results.py --all             # Check last 7 days
"""

import argparse
from datetime import datetime, timedelta
from typing import Optional

from data.result_matcher import ResultMatcher
from database.schema import SessionLocal, Simulation, Bet
from monitoring.logger import logger


def update_results_for_date(date_str: str, simulation_id: Optional[str] = None):
    """
    Update results for a specific date.

    Args:
        date_str: Date in YYYYMMDD format
        simulation_id: Optional simulation ID to limit updates
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"Fetching results for: {date_str}")
    logger.info(f"{'='*70}\n")

    matcher = ResultMatcher()

    try:
        # Fetch and update results
        stats = matcher.fetch_and_update_results(date_str, simulation_id)

        # Display results
        print(f"\n{'='*70}")
        print(f"RESULTS FOR {date_str}")
        print(f"{'='*70}")
        print(f"  Bets Checked:  {stats['total_checked']}")
        print(f"  Bets Updated:  {stats['updated']}")
        print(f"  ✅ Won:        {stats['won']}")
        print(f"  ❌ Lost:       {stats['lost']}")
        print(f"  ⚪ Push:       {stats['push']}")
        print(f"  ⚠️  Errors:     {stats['errors']}")
        print(f"{'='*70}\n")

        # Update affected simulations
        if stats['updated'] > 0:
            db = SessionLocal()
            try:
                # Find simulations that had bets updated
                updated_bets = db.query(Bet).filter(
                    Bet.game_date == date_str,
                    Bet.result_status.in_(['won', 'lost', 'push'])
                ).all()

                simulation_ids = set(bet.simulation_id for bet in updated_bets)

                print(f"Updating {len(simulation_ids)} affected simulations...\n")

                for sim_id in simulation_ids:
                    sim_stats = matcher.update_simulation_stats(sim_id)
                    agent_stats = matcher.update_agent_stats(sim_id)

                    print(f"Simulation {sim_stats['simulation_id'][:8]}:")
                    print(f"  Settled:    {sim_stats['settled_bets']}/{sim_stats['total_bets']} bets")
                    print(f"  Win Rate:   {sim_stats['win_rate']:.1f}%")
                    print(f"  ROI:        {sim_stats['roi']:+.2f}%")
                    print(f"  Profit:     €{sim_stats['profit']:+.2f}")
                    print(f"  Final Bank: €{sim_stats['final_bankroll']:.2f}")
                    print()

            finally:
                db.close()

        return stats

    except Exception as e:
        logger.error(f"Error updating results: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_simulation(simulation_id: str):
    """
    Update results for all bets in a specific simulation.

    Args:
        simulation_id: Simulation UUID
    """
    db = SessionLocal()
    try:
        simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()

        if not simulation:
            print(f"❌ Simulation {simulation_id} not found")
            return

        print(f"\n{'='*70}")
        print(f"UPDATING SIMULATION: {simulation_id}")
        print(f"{'='*70}\n")

        # Get all bets for this simulation
        bets = db.query(Bet).filter(Bet.simulation_id == simulation_id).all()
        dates_to_check = set(bet.game_date for bet in bets if bet.game_date and bet.result_status == 'pending')

        if not dates_to_check:
            print("No pending bets found for this simulation.")
            return

        print(f"Checking {len(dates_to_check)} dates...\n")

        total_stats = {
            'total_checked': 0,
            'updated': 0,
            'won': 0,
            'lost': 0,
            'push': 0,
            'errors': 0
        }

        matcher = ResultMatcher(db)

        for date_str in sorted(dates_to_check):
            print(f"Checking {date_str}...")
            stats = matcher.fetch_and_update_results(date_str, simulation_id)

            for key in total_stats:
                total_stats[key] += stats[key]

        # Update simulation stats
        sim_stats = matcher.update_simulation_stats(simulation_id)
        agent_stats = matcher.update_agent_stats(simulation_id)

        print(f"\n{'='*70}")
        print(f"FINAL RESULTS")
        print(f"{'='*70}")
        print(f"  Bets Updated:  {total_stats['updated']}/{total_stats['total_checked']}")
        print(f"  ✅ Won:        {total_stats['won']}")
        print(f"  ❌ Lost:       {total_stats['lost']}")
        print(f"  ⚪ Push:       {total_stats['push']}")
        print(f"\nSimulation Statistics:")
        print(f"  Win Rate:   {sim_stats['win_rate']:.1f}%")
        print(f"  ROI:        {sim_stats['roi']:+.2f}%")
        print(f"  Profit:     €{sim_stats['profit']:+.2f}")
        print(f"  Final Bank: €{sim_stats['final_bankroll']:.2f}")
        print(f"{'='*70}\n")

        print("Agent Performance:")
        for agent in agent_stats:
            print(f"  {agent['agent_name']}")
            print(f"    Bets: {agent['total_bets']} ({agent['wins']}W/{agent['losses']}L)")
            print(f"    Win Rate: {agent['win_rate']:.1f}%")
            print(f"    ROI: {agent['roi']:+.2f}%")
            print(f"    Profit: €{agent['profit']:+.2f}")
            print()

    finally:
        db.close()


def update_all_recent():
    """Update results for the last 7 days."""
    print(f"\n{'='*70}")
    print(f"UPDATING LAST 7 DAYS OF RESULTS")
    print(f"{'='*70}\n")

    dates = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i+1)
        dates.append(date.strftime('%Y%m%d'))

    for date_str in dates:
        update_results_for_date(date_str)
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Update bet results from live scores"
    )
    parser.add_argument(
        '--date',
        type=str,
        help="Date to check in YYYYMMDD format (default: yesterday)"
    )
    parser.add_argument(
        '--simulation-id',
        type=str,
        help="Update specific simulation only"
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help="Check last 7 days"
    )
    parser.add_argument(
        '--list-pending',
        action='store_true',
        help="List all simulations with pending bets"
    )

    args = parser.parse_args()

    if args.list_pending:
        # List simulations with pending bets
        db = SessionLocal()
        try:
            simulations = db.query(Simulation).filter(
                Simulation.status.in_(['in_progress', 'awaiting_results'])
            ).all()

            print(f"\n{'='*70}")
            print(f"SIMULATIONS WITH PENDING BETS")
            print(f"{'='*70}\n")

            for sim in simulations:
                pending_bets = db.query(Bet).filter(
                    Bet.simulation_id == sim.id,
                    Bet.result_status.in_([None, 'pending'])
                ).count()

                if pending_bets > 0:
                    print(f"{sim.id}")
                    print(f"  Created:      {sim.created_at}")
                    print(f"  Sport:        {sim.sport}")
                    print(f"  Total Bets:   {sim.total_bets or 0}")
                    print(f"  Pending:      {pending_bets}")
                    print()

            print(f"{'='*70}\n")

        finally:
            db.close()

    elif args.simulation_id:
        # Update specific simulation
        update_simulation(args.simulation_id)

    elif args.all:
        # Update last 7 days
        update_all_recent()

    else:
        # Update specific date or yesterday
        if args.date:
            date_str = args.date
        else:
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime('%Y%m%d')

        update_results_for_date(date_str)


if __name__ == '__main__':
    main()
