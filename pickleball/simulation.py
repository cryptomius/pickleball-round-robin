import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random

# Force light theme
st.set_page_config(page_title="Tournament Simulation", layout="wide", initial_sidebar_state="collapsed")

class TournamentSimulator:
    def __init__(self, total_players, gender_ratio=0.5, courts=6, match_duration=20, changeover_time=5):
        """
        Initialize tournament simulator
        total_players: total number of players in tournament
        gender_ratio: ratio of female players (0.5 means equal split)
        courts: number of courts available
        match_duration: duration of each match in minutes
        changeover_time: time between matches in minutes
        """
        self.total_players = total_players
        self.num_females = int(total_players * gender_ratio)
        self.num_males = total_players - self.num_females
        self.courts = courts
        self.match_duration = match_duration
        self.changeover_time = changeover_time
        
        # Create player lists
        self.male_players = [f"M{i+1}" for i in range(self.num_males)]
        self.female_players = [f"F{i+1}" for i in range(self.num_females)]
        self.all_players = self.male_players + self.female_players
        
        # Initialize tracking variables
        self.matches_played = []
        self.player_stats = {p: {
            "matches": 0, 
            "mens": 0, 
            "womens": 0, 
            "mixed": 0, 
            "wait_times": [], 
            "last_match_time": 0,  # Track last match time for wait time calculation
            "partners": set(),  # Track who they've played with
            "opponents": set()  # Track who they've played against
        } for p in self.all_players}
        self.current_time = 0  # in minutes
        
        # Track match type ratios
        self.match_type_counts = {"mens": 0, "womens": 0, "mixed": 0}
        
    def score_combination(self, players, available_players):
        """Score a potential combination of players based on various factors"""
        score = 0
        
        # Factor 1: Wait time priority
        wait_times = [self.current_time - self.player_stats[p]["last_match_time"] for p in players]
        max_wait_time = max(wait_times)
        score += max_wait_time * 3  # Heavily weight wait times
        
        # Factor 2: Match count balancing
        games_played = [self.player_stats[p]["matches"] for p in players]
        score -= max(games_played) * 2  # Penalize players with many games
        
        # Factor 3: Player interaction history
        for i, p1 in enumerate(players):
            for p2 in players[i+1:]:
                # Penalize if they've played together or against each other
                if p2 in self.player_stats[p1]["partners"]:
                    score -= 3
                if p2 in self.player_stats[p1]["opponents"]:
                    score -= 2
        
        return score

    def get_optimal_players(self, available_players, count, gender=None):
        """Get the optimal combination of players based on various factors"""
        if gender:
            candidates = [p for p in available_players if (p.startswith("M") if gender == "M" else p.startswith("F"))]
        else:
            candidates = available_players
            
        if len(candidates) < count:
            return None
            
        # Try different combinations of players
        best_score = float('-inf')
        best_combination = None
        
        from itertools import combinations
        for combo in combinations(candidates, count):
            score = self.score_combination(combo, available_players)
            if score > best_score:
                best_score = score
                best_combination = combo
        
        return list(best_combination) if best_combination else None

    def generate_match(self, available_players):
        """Generate a match based on available players with enhanced selection logic"""
        available_males = [p for p in available_players if p.startswith("M")]
        available_females = [p for p in available_players if p.startswith("F")]
        
        # Calculate current ratios for each gender
        male_ratio = 0
        female_ratio = 0
        
        total_male_matches = sum(self.player_stats[p]["mens"] for p in self.male_players)
        total_male_mixed = sum(self.player_stats[p]["mixed"] for p in self.male_players)
        if total_male_matches + total_male_mixed > 0:
            male_ratio = total_male_mixed / (total_male_matches + total_male_mixed)
            
        total_female_matches = sum(self.player_stats[p]["womens"] for p in self.female_players)
        total_female_mixed = sum(self.player_stats[p]["mixed"] for p in self.female_players)
        if total_female_matches + total_female_mixed > 0:
            female_ratio = total_female_mixed / (total_female_matches + total_female_mixed)
        
        # Determine available match types
        match_types = []
        if len(available_males) >= 4 and male_ratio > 0.5:
            match_types.append("mens")
        if len(available_females) >= 4 and female_ratio > 0.5:
            match_types.append("womens")
        if len(available_males) >= 2 and len(available_females) >= 2 and (male_ratio < 0.5 or female_ratio < 0.5):
            match_types.append("mixed")
            
        # If no preferred types available, fall back to all possible types
        if not match_types:
            if len(available_males) >= 4:
                match_types.append("mens")
            if len(available_females) >= 4:
                match_types.append("womens")
            if len(available_males) >= 2 and len(available_females) >= 2:
                match_types.append("mixed")
            
        if not match_types:
            return None
            
        match_type = random.choice(match_types)
        
        if match_type == "mens":
            players = self.get_optimal_players(available_males, 4, "M")
            if not players:
                return None
            team1 = players[:2]
            team2 = players[2:]
        elif match_type == "womens":
            players = self.get_optimal_players(available_females, 4, "F")
            if not players:
                return None
            team1 = players[:2]
            team2 = players[2:]
        else:  # mixed
            males = self.get_optimal_players(available_males, 2, "M")
            females = self.get_optimal_players(available_females, 2, "F")
            if not males or not females:
                return None
            team1 = [males[0], females[0]]
            team2 = [males[1], females[1]]
            
        # Update player interaction tracking
        for p1 in team1:
            self.player_stats[p1]["partners"].add(team1[1] if p1 == team1[0] else team1[0])
            for p2 in team2:
                self.player_stats[p1]["opponents"].add(p2)
                
        for p1 in team2:
            self.player_stats[p1]["partners"].add(team2[1] if p1 == team2[0] else team2[0])
            for p2 in team1:
                self.player_stats[p1]["opponents"].add(p2)
            
        return {
            "type": match_type,
            "team1": team1,
            "team2": team2,
            "start_time": self.current_time,
            "end_time": self.current_time + self.match_duration
        }
        
    def run_simulation(self, duration_hours=6):
        """Run the tournament simulation"""
        duration_minutes = duration_hours * 60
        active_matches = []  # Matches currently being played
        
        while self.current_time < duration_minutes:
            # Check for finished matches
            active_matches = [m for m in active_matches if m["end_time"] > self.current_time]
            
            # Get players in active matches
            busy_players = set()
            for match in active_matches:
                busy_players.update(match["team1"] + match["team2"])
                
            # Generate new matches for available courts
            available_players = [p for p in self.all_players if p not in busy_players]
            while len(active_matches) < self.courts and len(available_players) >= 4:
                new_match = self.generate_match(available_players)
                if new_match is None:
                    break
                    
                active_matches.append(new_match)
                self.matches_played.append(new_match)
                
                # Update player stats
                for player in new_match["team1"] + new_match["team2"]:
                    self.player_stats[player]["matches"] += 1
                    self.player_stats[player][new_match["type"]] += 1
                    # Calculate wait time (time since last match or start of tournament)
                    last_match_time = max([m["end_time"] for m in self.matches_played 
                                         if player in (m["team1"] + m["team2"]) 
                                         and m != new_match] + [0])
                    wait_time = new_match["start_time"] - last_match_time if last_match_time > 0 else 0
                    self.player_stats[player]["wait_times"].append(wait_time)
                    self.player_stats[player]["last_match_time"] = new_match["end_time"]
                
                # Update available players
                busy_players.update(new_match["team1"] + new_match["team2"])
                available_players = [p for p in self.all_players if p not in busy_players]
            
            # Advance time to next event (match end or changeover)
            if active_matches:
                next_end_time = min(m["end_time"] for m in active_matches)
                self.current_time = next_end_time + self.changeover_time
            else:
                self.current_time += self.match_duration

def run_tournament_analysis(num_players):
    """Run tournament analysis for a given number of players"""
    simulator = TournamentSimulator(num_players)
    simulator.run_simulation()
    
    # Calculate statistics
    match_counts = [stats["matches"] for stats in simulator.player_stats.values()]
    mens_counts_male = [stats["mens"] for player, stats in simulator.player_stats.items() if player.startswith("M")]
    mixed_counts_male = [stats["mixed"] for player, stats in simulator.player_stats.items() if player.startswith("M")]
    womens_counts_female = [stats["womens"] for player, stats in simulator.player_stats.items() if player.startswith("F")]
    mixed_counts_female = [stats["mixed"] for player, stats in simulator.player_stats.items() if player.startswith("F")]
    wait_times = [wait for stats in simulator.player_stats.values() for wait in stats["wait_times"]]
    
    # Count match types
    match_type_counts = {
        "mens": len([m for m in simulator.matches_played if m["type"] == "mens"]),
        "womens": len([m for m in simulator.matches_played if m["type"] == "womens"]),
        "mixed": len([m for m in simulator.matches_played if m["type"] == "mixed"])
    }
    
    return {
        "match_counts": {
            "min": min(match_counts),
            "max": max(match_counts),
            "avg": np.mean(match_counts),
            "all_counts": match_counts  # Store all match counts for box plot
        },
        "mens_counts_male": {
            "min": min(mens_counts_male),
            "max": max(mens_counts_male),
            "avg": np.mean(mens_counts_male)
        },
        "mixed_counts_male": {
            "min": min(mixed_counts_male),
            "max": max(mixed_counts_male),
            "avg": np.mean(mixed_counts_male)
        },
        "womens_counts_female": {
            "min": min(womens_counts_female),
            "max": max(womens_counts_female),
            "avg": np.mean(womens_counts_female)
        },
        "mixed_counts_female": {
            "min": min(mixed_counts_female),
            "max": max(mixed_counts_female),
            "avg": np.mean(mixed_counts_female)
        },
        "wait_times": {
            "min": min(wait_times),
            "max": max(wait_times),
            "avg": np.mean(wait_times),
            "all_times": wait_times  # Store all wait times for box plot
        },
        "match_type_counts": match_type_counts
    }

def main():
    st.title("Pickleball Tournament Simulation Analysis")
    st.write("Compare Standard vs Rally Scoring")
    
    # Run simulations for player counts 20-60 with both scoring systems
    player_counts = list(range(20, 61, 2))
    standard_results = []
    rally_results = []
    
    # Initialize progress bars
    progress_text = "Running simulations..."
    progress_bar = st.progress(0, text=progress_text)
    total_iterations = len(player_counts) * 2  # For both standard and rally scoring
    current_iteration = 0
    
    # Standard scoring (15-20 min games)
    for count in player_counts:
        simulator = TournamentSimulator(count, match_duration=17.5)  # Average of 15-20 minutes
        simulator.run_simulation()
        
        # Calculate median games per player
        games_per_player = [stats["matches"] for stats in simulator.player_stats.values()]
        median_games = np.median(games_per_player)
        
        # Calculate median wait time per player
        all_wait_times = [wait for stats in simulator.player_stats.values() for wait in stats["wait_times"]]
        median_wait = np.median(all_wait_times) if all_wait_times else 0
        
        result = {
            "players": count,
            "median_games": median_games,
            "median_wait_time": median_wait
        }
        standard_results.append(result)
        
        # Update progress
        current_iteration += 1
        progress_bar.progress(current_iteration / total_iterations, 
                            text=f"{progress_text} Standard scoring: {count} players")
    
    # Rally scoring (10-12 min games)
    for count in player_counts:
        simulator = TournamentSimulator(count, match_duration=11)  # Average of 10-12 minutes
        simulator.run_simulation()
        
        # Calculate median games per player
        games_per_player = [stats["matches"] for stats in simulator.player_stats.values()]
        median_games = np.median(games_per_player)
        
        # Calculate median wait time per player
        all_wait_times = [wait for stats in simulator.player_stats.values() for wait in stats["wait_times"]]
        median_wait = np.median(all_wait_times) if all_wait_times else 0
        
        result = {
            "players": count,
            "median_games": median_games,
            "median_wait_time": median_wait
        }
        rally_results.append(result)
        
        # Update progress
        current_iteration += 1
        progress_bar.progress(current_iteration / total_iterations, 
                            text=f"{progress_text} Rally scoring: {count} players")
    
    # Clear the progress bar
    progress_bar.empty()
    
    standard_df = pd.DataFrame(standard_results)
    rally_df = pd.DataFrame(rally_results)
    
    # Plot median games per player comparison
    st.subheader("Median Games per Player Comparison")
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=standard_df['players'],
            y=standard_df['median_games'],
            mode='lines',
            name='Standard Scoring (17.5 min)',
            line=dict(color='blue', width=3)
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=rally_df['players'],
            y=rally_df['median_games'],
            mode='lines',
            name='Rally Scoring (11 min)',
            line=dict(color='red', width=3)
        )
    )
    
    fig.update_layout(
        xaxis_title="Number of Players",
        yaxis_title="Median Games per Player",
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Plot median wait times comparison
    st.subheader("Median Wait Time Comparison")
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=standard_df['players'],
            y=standard_df['median_wait_time'],
            mode='lines',
            name='Standard Scoring (17.5 min)',
            line=dict(color='blue', width=3)
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=rally_df['players'],
            y=rally_df['median_wait_time'],
            mode='lines',
            name='Rally Scoring (11 min)',
            line=dict(color='red', width=3)
        )
    )
    
    fig.update_layout(
        xaxis_title="Number of Players",
        yaxis_title="Median Wait Time (minutes)",
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Show detailed comparison for a specific player count
    st.subheader("Detailed Comparison for Specific Player Count")
    selected_count = st.selectbox("Select number of players", player_counts, index=player_counts.index(40))
    
    # Show progress for detailed stats calculation
    detailed_progress = st.progress(0, text="Calculating detailed statistics...")
    
    # Standard scoring stats calculation
    standard_stats = standard_df[standard_df["players"] == selected_count].iloc[0]
    standard_simulator = TournamentSimulator(selected_count, match_duration=17.5)
    standard_simulator.run_simulation()
    detailed_progress.progress(0.25, text="Calculating standard scoring statistics...")
    
    # Calculate standard scoring medians
    standard_mens_per_male = [stats["mens"] for player, stats in standard_simulator.player_stats.items() if player.startswith("M")]
    standard_mixed_per_male = [stats["mixed"] for player, stats in standard_simulator.player_stats.items() if player.startswith("M")]
    standard_womens_per_female = [stats["womens"] for player, stats in standard_simulator.player_stats.items() if player.startswith("F")]
    standard_mixed_per_female = [stats["mixed"] for player, stats in standard_simulator.player_stats.items() if player.startswith("F")]
    detailed_progress.progress(0.5, text="Calculating rally scoring statistics...")
    
    # Rally scoring stats calculation
    rally_stats = rally_df[rally_df["players"] == selected_count].iloc[0]
    rally_simulator = TournamentSimulator(selected_count, match_duration=11)
    rally_simulator.run_simulation()
    detailed_progress.progress(0.75, text="Processing final calculations...")
    
    # Calculate rally scoring medians
    rally_mens_per_male = [stats["mens"] for player, stats in rally_simulator.player_stats.items() if player.startswith("M")]
    rally_mixed_per_male = [stats["mixed"] for player, stats in rally_simulator.player_stats.items() if player.startswith("M")]
    rally_womens_per_female = [stats["womens"] for player, stats in rally_simulator.player_stats.items() if player.startswith("F")]
    rally_mixed_per_female = [stats["mixed"] for player, stats in rally_simulator.player_stats.items() if player.startswith("F")]
    
    # Clear the progress bar
    detailed_progress.empty()
    
    # Display stats in two columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Standard Scoring (17.5 min)")
        st.metric("Median Games per Player", int(standard_stats['median_games']))
        st.metric("Median Wait Time", f"{int(standard_stats['median_wait_time'])} min")
        st.metric("Men's Doubles per Male", int(np.median(standard_mens_per_male)))
        st.metric("Mixed Doubles per Male", int(np.median(standard_mixed_per_male)))
        st.metric("Women's Doubles per Female", int(np.median(standard_womens_per_female)))
        st.metric("Mixed Doubles per Female", int(np.median(standard_mixed_per_female)))
    
    with col2:
        st.markdown("### Rally Scoring (11 min)")
        st.metric("Median Games per Player", int(rally_stats['median_games']))
        st.metric("Median Wait Time", f"{int(rally_stats['median_wait_time'])} min")
        st.metric("Men's Doubles per Male", int(np.median(rally_mens_per_male)))
        st.metric("Mixed Doubles per Male", int(np.median(rally_mixed_per_male)))
        st.metric("Women's Doubles per Female", int(np.median(rally_womens_per_female)))
        st.metric("Mixed Doubles per Female", int(np.median(rally_mixed_per_female)))

if __name__ == "__main__":
    main()
