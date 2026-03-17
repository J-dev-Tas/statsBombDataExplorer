#!/usr/bin/env python3
"""
StatsBomb Match Explorer
Interactive terminal script to browse competitions, seasons, matches, and events.
"""

import pandas as pd
import json
from pathlib import Path
import sys


class MatchExplorer:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / 'data'
        self.competitions_file = self.data_dir / 'competitions.json'
        self.matches_dir = self.data_dir / 'matches'
        self.events_dir = self.data_dir / 'events'
        
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', 100)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 50)
        
    def load_competitions(self):
        with open(self.competitions_file, 'r') as f:
            competitions_data = json.load(f)
        return pd.json_normalize(competitions_data)
    
    def load_matches_for_season(self, competition_id, season_id):
        match_file = self.matches_dir / str(competition_id) / f"{season_id}.json"
        
        if not match_file.exists():
            print(f"No matches found for competition {competition_id}, season {season_id}")
            return pd.DataFrame()
        
        with open(match_file, 'r') as f:
            matches_data = json.load(f)
        
        return pd.json_normalize(matches_data)
    
    def load_events(self, match_id):
        event_file = self.events_dir / f"{match_id}.json"
        
        if not event_file.exists():
            print(f"No events found for match {match_id}")
            return pd.DataFrame()
        
        with open(event_file, 'r') as f:
            events_data = json.load(f)
        
        return pd.json_normalize(events_data)
    
    def clear_screen(self):
        print("\n" * 2)
    
    def display_menu(self, title, options, show_numbers=True):
        self.clear_screen()
        print("=" * 70)
        print(f"  {title}")
        print("=" * 70)
        print()
        
        for idx, option in enumerate(options, 1):
            if show_numbers:
                print(f"  {idx}. {option}")
            else:
                print(f"  {option}")
        
        print()
        print("-" * 70)
        
    def get_user_choice(self, max_value, allow_back=True):
        while True:
            if allow_back:
                choice = input(f"Enter your choice (1-{max_value}, or 'b' to go back, 'q' to quit): ").strip().lower()
            else:
                choice = input(f"Enter your choice (1-{max_value}, or 'q' to quit): ").strip().lower()
            
            if choice == 'q':
                print("\nGoodbye!")
                sys.exit(0)
            
            if allow_back and choice == 'b':
                return 'back'
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= max_value:
                    return choice_num - 1  # Return 0-based index
                else:
                    print(f"Please enter a number between 1 and {max_value}")
            except ValueError:
                print("Invalid input. Please enter a number.")
    
    def select_competition(self, df_competitions):
        competitions = df_competitions.groupby(
            ['competition_id', 'competition_name', 'country_name']
        ).size().reset_index()[['competition_id', 'competition_name', 'country_name']]
        
        options = [
            f"{row['competition_name']} ({row['country_name']})"
            for _, row in competitions.iterrows()
        ]
        
        self.display_menu("SELECT COMPETITION", options)
        choice = self.get_user_choice(len(options), allow_back=False)
        
        return competitions.iloc[choice]
    
    def select_season(self, df_competitions, competition_id):
        seasons = df_competitions[
            df_competitions['competition_id'] == competition_id
        ][['season_id', 'season_name']].sort_values('season_name', ascending=False)
        
        options = [row['season_name'] for _, row in seasons.iterrows()]
        
        self.display_menu("SELECT SEASON", options)
        choice = self.get_user_choice(len(options))
        
        if choice == 'back':
            return None
        
        return seasons.iloc[choice]
    
    def select_match(self, df_matches):
        if len(df_matches) == 0:
            print("No matches available for this season.")
            input("Press Enter to continue...")
            return None
        
        options = []
        for _, match in df_matches.iterrows():
            home_team = match.get('home_team.home_team_name', 'Unknown')
            away_team = match.get('away_team.away_team_name', 'Unknown')
            match_date = match.get('match_date', 'Unknown date')
            home_score = match.get('home_score', '?')
            away_score = match.get('away_score', '?')
            
            options.append(
                f"{match_date} | {home_team} {home_score} - {away_score} {away_team}"
            )
        
        self.display_menu("SELECT MATCH", options)
        choice = self.get_user_choice(len(options))
        
        if choice == 'back':
            return None
        
        return df_matches.iloc[choice]
    
    def display_events(self, df_events, match_info):
        self.clear_screen()
        print("=" * 70)
        print(f"  MATCH EVENTS")
        print("=" * 70)
        
        home_team = match_info.get('home_team.home_team_name', 'Unknown')
        away_team = match_info.get('away_team.away_team_name', 'Unknown')
        match_date = match_info.get('match_date', 'Unknown')
        home_score = match_info.get('home_score', '?')
        away_score = match_info.get('away_score', '?')
        
        print()
        print(f"  {home_team} {home_score} - {away_score} {away_team}")
        print(f"  Date: {match_date}")
        print()
        print("=" * 70)
        print()
        
        print(f"Total Events: {len(df_events)}")
        print()
        print("Event Types:")
        print("-" * 70)
        event_counts = df_events['type.name'].value_counts()
        for event_type, count in event_counts.head(15).items():
            print(f"  {event_type:.<40} {count:>5}")
        
        if len(event_counts) > 15:
            print(f"  ... and {len(event_counts) - 15} more event types")
        
        print()
        print("=" * 70)
        print()
        
        while True:
            print("Options:")
            print("  1. View all events")
            print("  2. Filter by event type")
            print("  3. Filter by team")
            print("  4. Filter by player")
            print("  5. View goals only")
            print("  6. View shots only")
            print("  7. Back to match selection")
            print()
            
            choice = input("Enter your choice (1-7): ").strip()
            
            if choice == '1':
                self.view_all_events(df_events)
            elif choice == '2':
                self.filter_by_event_type(df_events)
            elif choice == '3':
                self.filter_by_team(df_events)
            elif choice == '4':
                self.filter_by_player(df_events)
            elif choice == '5':
                self.view_goals(df_events)
            elif choice == '6':
                self.view_shots(df_events)
            elif choice == '7':
                break
            else:
                print("Invalid choice. Please try again.")
    
    def view_all_events(self, df_events):
        self.clear_screen()
        print("ALL EVENTS")
        print("=" * 70)
        
        columns = ['minute', 'second', 'type.name', 'team.name', 'player.name']
        available_cols = [col for col in columns if col in df_events.columns]
        
        print(df_events[available_cols].to_string(index=False))
        print()
        input("Press Enter to continue...")
    
    def filter_by_event_type(self, df_events):
        event_types = df_events['type.name'].unique()
        
        self.clear_screen()
        print("SELECT EVENT TYPE")
        print("=" * 70)
        
        for idx, event_type in enumerate(sorted(event_types), 1):
            print(f"  {idx}. {event_type}")
        
        print()
        choice = input(f"Enter choice (1-{len(event_types)}): ").strip()
        
        try:
            selected_type = sorted(event_types)[int(choice) - 1]
            filtered = df_events[df_events['type.name'] == selected_type]
            
            self.clear_screen()
            print(f"EVENTS: {selected_type}")
            print("=" * 70)
            
            columns = ['minute', 'second', 'team.name', 'player.name']
            available_cols = [col for col in columns if col in filtered.columns]
            
            print(filtered[available_cols].to_string(index=False))
            print()
            print(f"Total: {len(filtered)} events")
        except (ValueError, IndexError):
            print("Invalid choice.")
        
        print()
        input("Press Enter to continue...")
    
    def filter_by_team(self, df_events):
        if 'team.name' not in df_events.columns:
            print("Team information not available.")
            input("Press Enter to continue...")
            return
        
        teams = df_events['team.name'].unique()
        
        self.clear_screen()
        print("SELECT TEAM")
        print("=" * 70)
        
        for idx, team in enumerate(teams, 1):
            print(f"  {idx}. {team}")
        
        print()
        choice = input(f"Enter choice (1-{len(teams)}): ").strip()
        
        try:
            selected_team = teams[int(choice) - 1]
            filtered = df_events[df_events['team.name'] == selected_team]
            
            self.clear_screen()
            print(f"EVENTS: {selected_team}")
            print("=" * 70)
            
            columns = ['minute', 'second', 'type.name', 'player.name']
            available_cols = [col for col in columns if col in filtered.columns]
            
            print(filtered[available_cols].to_string(index=False))
            print()
            print(f"Total: {len(filtered)} events")
        except (ValueError, IndexError):
            print("Invalid choice.")
        
        print()
        input("Press Enter to continue...")
    
    def filter_by_player(self, df_events):
        if 'player.name' not in df_events.columns:
            print("Player information not available.")
            input("Press Enter to continue...")
            return
        
        players = df_events['player.name'].dropna().unique()
        
        self.clear_screen()
        print("SELECT PLAYER (showing first 50)")
        print("=" * 70)
        
        for idx, player in enumerate(sorted(players)[:50], 1):
            print(f"  {idx}. {player}")
        
        print()
        choice = input(f"Enter choice (1-{min(50, len(players))}): ").strip()
        
        try:
            selected_player = sorted(players)[int(choice) - 1]
            filtered = df_events[df_events['player.name'] == selected_player]
            
            self.clear_screen()
            print(f"EVENTS: {selected_player}")
            print("=" * 70)
            
            columns = ['minute', 'second', 'type.name', 'team.name']
            available_cols = [col for col in columns if col in filtered.columns]
            
            print(filtered[available_cols].to_string(index=False))
            print()
            print(f"Total: {len(filtered)} events")
        except (ValueError, IndexError):
            print("Invalid choice.")
        
        print()
        input("Press Enter to continue...")
    
    def view_goals(self, df_events):
        goals = df_events[
            (df_events['type.name'] == 'Shot') & 
            (df_events.get('shot.outcome.name', pd.Series()) == 'Goal')
        ]
        
        self.clear_screen()
        print("GOALS")
        print("=" * 70)
        
        if len(goals) == 0:
            print("No goals in this match.")
        else:
            columns = ['minute', 'second', 'team.name', 'player.name']
            available_cols = [col for col in columns if col in goals.columns]
            
            print(goals[available_cols].to_string(index=False))
            print()
            print(f"Total goals: {len(goals)}")
        
        print()
        input("Press Enter to continue...")
    
    def view_shots(self, df_events):
        shots = df_events[df_events['type.name'] == 'Shot']
        
        self.clear_screen()
        print("SHOTS")
        print("=" * 70)
        
        if len(shots) == 0:
            print("No shots in this match.")
        else:
            columns = ['minute', 'second', 'team.name', 'player.name', 'shot.outcome.name']
            available_cols = [col for col in columns if col in shots.columns]
            
            print(shots[available_cols].to_string(index=False))
            print()
            print(f"Total shots: {len(shots)}")
        
        print()
        input("Press Enter to continue...")
    
    def run(self):
        print("\n" + "=" * 70)
        print("  StatsBomb Match Explorer")
        print("=" * 70)
        print("\n  Loading data...\n")
        
        df_competitions = self.load_competitions()
        
        print(f"  ✓ Loaded {len(df_competitions)} competition/season combinations\n")
        
        while True:
            competition = self.select_competition(df_competitions)
            
            while True:
                season = self.select_season(df_competitions, competition['competition_id'])
                if season is None:
                    break
                
                df_matches = self.load_matches_for_season(
                    competition['competition_id'],
                    season['season_id']
                )
                
                while True:
                    match = self.select_match(df_matches)
                    if match is None:
                        break
                    
                    df_events = self.load_events(match['match_id'])
                    
                    if len(df_events) > 0:
                        self.display_events(df_events, match)
                    else:
                        print("No events found for this match.")
                        input("Press Enter to continue...")


def main():
    explorer = MatchExplorer()
    try:
        explorer.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
