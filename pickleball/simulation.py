import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random

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
        self.player_stats = {p: {"matches": 0, "mens": 0, "womens": 0, "mixed": 0, "wait_times": []} for p in self.all_players}
        self.current_time = 0  # in minutes
        
    def generate_match(self, available_players):
        """Generate a match based on available players"""
        available_males = [p for p in available_players if p.startswith("M")]
        available_females = [p for p in available_players if p.startswith("F")]
        
        # Determine match type probabilities based on available players
        match_types = []
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
            players = random.sample(available_males, 4)
            team1 = players[:2]
            team2 = players[2:]
        elif match_type == "womens":
            players = random.sample(available_females, 4)
            team1 = players[:2]
            team2 = players[2:]
        else:  # mixed
            males = random.sample(available_males, 2)
            females = random.sample(available_females, 2)
            team1 = [males[0], females[0]]
            team2 = [males[1], females[1]]
            
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
            "avg": np.mean(match_counts)
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
            "avg": np.mean(wait_times)
        },
        "match_type_counts": match_type_counts
    }

def main():
    st.title("Pickleball Tournament Simulation Analysis")
    st.write("Analyze tournament dynamics for different player counts")
    
    # Run simulations for player counts 30-60
    player_counts = list(range(30, 61, 2))
    results = []
    
    for count in player_counts:
        result = run_tournament_analysis(count)
        results.append({
            "players": count,
            **result["match_counts"],
            "mens_matches": result["match_type_counts"]["mens"],
            "womens_matches": result["match_type_counts"]["womens"],
            "mixed_matches": result["match_type_counts"]["mixed"],
            "avg_wait_time": result["wait_times"]["avg"],
            "max_wait_time": result["wait_times"]["max"],
            "mens_counts_male_min": result["mens_counts_male"]["min"],
            "mens_counts_male_max": result["mens_counts_male"]["max"],
            "mens_counts_male_avg": result["mens_counts_male"]["avg"],
            "mixed_counts_male_min": result["mixed_counts_male"]["min"],
            "mixed_counts_male_max": result["mixed_counts_male"]["max"],
            "mixed_counts_male_avg": result["mixed_counts_male"]["avg"],
            "womens_counts_female_min": result["womens_counts_female"]["min"],
            "womens_counts_female_max": result["womens_counts_female"]["max"],
            "womens_counts_female_avg": result["womens_counts_female"]["avg"],
            "mixed_counts_female_min": result["mixed_counts_female"]["min"],
            "mixed_counts_female_max": result["mixed_counts_female"]["max"],
            "mixed_counts_female_avg": result["mixed_counts_female"]["avg"]
        })
    
    df = pd.DataFrame(results)
    
    # Plot match distribution
    st.subheader("Match Count Distribution by Player Count")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["players"], y=df["min"], name="Min Matches", line=dict(dash="dash")))
    fig.add_trace(go.Scatter(x=df["players"], y=df["max"], name="Max Matches", line=dict(dash="dash")))
    fig.add_trace(go.Scatter(x=df["players"], y=df["avg"], name="Avg Matches"))
    fig.update_layout(
        xaxis_title="Number of Players",
        yaxis_title="Number of Matches",
        title="Match Distribution per Player"
    )
    st.plotly_chart(fig)
    
    # Plot match type distribution
    st.subheader("Match Type Distribution")
    match_type_df = pd.DataFrame({
        "Players": df["players"],
        "Men's Doubles": df["mens_matches"],
        "Women's Doubles": df["womens_matches"],
        "Mixed Doubles": df["mixed_matches"]
    })
    fig = px.line(match_type_df, x="Players", y=["Men's Doubles", "Women's Doubles", "Mixed Doubles"],
                  title="Number of Matches by Type")
    st.plotly_chart(fig)
    
    # Plot wait times
    st.subheader("Wait Time Analysis")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["players"], y=df["avg_wait_time"], name="Avg Wait Time"))
    fig.add_trace(go.Scatter(x=df["players"], y=df["max_wait_time"], name="Max Wait Time", line=dict(dash="dash")))
    fig.update_layout(
        xaxis_title="Number of Players",
        yaxis_title="Wait Time (minutes)",
        title="Player Wait Times"
    )
    st.plotly_chart(fig)
    
    # Show detailed statistics for a specific player count
    st.subheader("Detailed Statistics for Specific Player Count")
    selected_count = st.selectbox("Select number of players", player_counts)
    selected_stats = df[df["players"] == selected_count].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Matches per Player", f"{selected_stats['avg']:.1f}")
        st.metric("Men's Doubles per Male", f"{selected_stats['mens_counts_male_avg']:.1f}")
        st.metric("Mixed Doubles per Male", f"{selected_stats['mixed_counts_male_avg']:.1f}")
    with col2:
        st.metric("Min Matches", selected_stats["min"])
        st.metric("Women's Doubles per Female", f"{selected_stats['womens_counts_female_avg']:.1f}")
        st.metric("Mixed Doubles per Female", f"{selected_stats['mixed_counts_female_avg']:.1f}")
    with col3:
        st.metric("Max Matches", selected_stats["max"])
        st.metric("Average Wait Time", f"{selected_stats['avg_wait_time']:.1f} min")
        st.metric("Max Wait Time", f"{selected_stats['max_wait_time']:.1f} min")

if __name__ == "__main__":
    main()
