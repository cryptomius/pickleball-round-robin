class PickleballSimulation {
    constructor() {
        this.svg = d3.select('#courtLayout');
        this.width = 1000;
        this.height = 600;
        this.svg.attr('width', this.width).attr('height', this.height);
        
        this.players = [];
        this.courts = [];
        this.matches = [];
        this.pendingMatches = []; // Track matches waiting for courts
        this.timeElapsed = 0;
        this.isRunning = false;
        this.matchDuration = 17.5; // Default to standard scoring (17.5 minutes)
        this.totalDuration = 360; // 6 hours in minutes
        this.simulationTimer = null; // Add timer reference
        
        // Set up the court layout
        this.setupCourts();
        this.setupControls();
        this.setupTimeSlider();
    }

    setupCourts() {
        // Waiting area on the left
        this.svg.append('rect')
            .attr('class', 'waiting-area')
            .attr('x', 50)
            .attr('y', 50)
            .attr('width', 300)
            .attr('height', 500);

        // 6 courts on the right (3x2 grid)
        const courtWidth = 180;
        const courtHeight = 240;
        const startX = 400;
        const startY = 50;
        const padding = 20;

        for (let row = 0; row < 2; row++) {
            for (let col = 0; col < 3; col++) {
                const x = startX + col * (courtWidth + padding);
                const y = startY + row * (courtHeight + padding);
                
                this.courts.push({
                    id: row * 3 + col,
                    x, y,
                    width: courtWidth,
                    height: courtHeight,
                    players: []
                });

                // Draw court rectangle
                this.svg.append('rect')
                    .attr('class', 'court')
                    .attr('x', x)
                    .attr('y', y)
                    .attr('width', courtWidth)
                    .attr('height', courtHeight);

                // Draw net (black horizontal line in the middle)
                this.svg.append('line')
                    .attr('class', 'net')
                    .attr('x1', x)
                    .attr('y1', y + courtHeight/2)
                    .attr('x2', x + courtWidth)
                    .attr('y2', y + courtHeight/2)
                    .attr('stroke', 'black')
                    .attr('stroke-width', 2);
            }
        }
    }

    setupControls() {
        d3.select('#startSimulation').on('click', () => this.start());
        d3.select('#pauseSimulation').on('click', () => this.pause());
        d3.select('#resetSimulation').on('click', () => this.reset());
        
        // Add player count change listener with clean reset
        d3.select('#playerCount').on('change', () => {
            this.reset();
            this.start();
        });
        
        // Set standard scoring as default and add change listener
        const scoringSelect = d3.select('#scoringSystem');
        scoringSelect.node().value = 'standard';
        this.matchDuration = 17.5; // Set initial duration to standard scoring
        
        scoringSelect.on('change', () => {
            this.matchDuration = scoringSelect.node().value === 'rally' ? 11 : 17.5;
            this.reset();
            this.start();
        });
    }

    setupTimeSlider() {
        const slider = document.getElementById('timeSlider');
        noUiSlider.create(slider, {
            start: 0,
            connect: true,
            range: {
                'min': 0,
                'max': this.totalDuration
            }
        });

        slider.noUiSlider.on('update', (values) => {
            if (!this.isRunning) {
                this.timeElapsed = parseInt(values[0]);
                this.updateSimulation();
            }
        });
    }

    initializePlayers() {
        const playerCount = parseInt(d3.select('#playerCount').node().value);
        const maleCount = Math.floor(playerCount / 2);
        const femaleCount = playerCount - maleCount;
        
        this.players = [];
        
        // Create male players (blue)
        for (let i = 0; i < maleCount; i++) {
            this.players.push({
                id: i + 1,
                gender: 'M',
                waitTime: 0,
                inMatch: false,
                gamesPlayed: 0,
                x: 0,
                y: 0,
                originalX: 0,  // Store original position
                originalY: 0
            });
        }
        
        // Create female players (pink)
        for (let i = 0; i < femaleCount; i++) {
            this.players.push({
                id: maleCount + i + 1,
                gender: 'F',
                waitTime: 0,
                inMatch: false,
                gamesPlayed: 0,
                x: 0,
                y: 0,
                originalX: 0,  // Store original position
                originalY: 0
            });
        }

        this.positionWaitingPlayers(true);  // true indicates initial positioning
    }

    positionWaitingPlayers(isInitial = false) {
        const waitingPlayers = this.players.filter(p => !p.inMatch);
        const cols = 6;
        const spacing = 40;
        const startX = 80;
        const startY = 80;

        waitingPlayers.forEach((player, i) => {
            const row = Math.floor(i / cols);
            const col = i % cols;
            const newX = startX + col * spacing;
            const newY = startY + row * spacing;
            
            if (isInitial) {
                // Store original position during initialization
                player.originalX = newX;
                player.originalY = newY;
                player.x = newX;
                player.y = newY;
            } else {
                // Return to original position when coming back to waiting area
                player.x = player.originalX;
                player.y = player.originalY;
            }
        });

        this.updatePlayerVisuals();
    }

    updatePlayerVisuals() {
        // Update existing players
        const players = this.svg.selectAll('.player')
            .data(this.players, d => d.id);

        // Remove old players
        players.exit().remove();

        // Add new players
        const newPlayers = players.enter()
            .append('g')
            .attr('class', 'player');

        newPlayers.append('circle')
            .attr('r', 15);

        newPlayers.append('text')
            .attr('class', 'player-id')
            .text(d => d.id);

        // Add wait time text element
        newPlayers.append('text')
            .attr('class', 'wait-time')
            .attr('x', 12)
            .attr('y', -12)
            .style('font-size', '10px')
            .style('fill', 'black');

        // Add games played counter
        newPlayers.append('text')
            .attr('class', 'games-played')
            .attr('x', -12)
            .attr('y', -12)
            .style('font-size', '10px')
            .style('fill', 'black');

        // Update all players
        this.svg.selectAll('.player')
            .attr('transform', d => `translate(${d.x},${d.y})`);

        // Update circles
        this.svg.selectAll('.player circle')
            .style('fill', d => {
                const baseColor = d.gender === 'M' ? 'blue' : 'pink';
                if (d.inMatch) return baseColor; // Reset darkness when in match
                const opacity = Math.max(0.3, 1 - (Math.floor(d.waitTime / 5) * 0.2)); // Darken by 20% every 5 minutes
                return d3.color(baseColor).darker(1 - opacity);
            });

        // Update wait time display
        this.svg.selectAll('.player .wait-time')
            .text(d => d.inMatch ? '' : d.waitTime > 0 ? d.waitTime : '')
            .style('display', d => d.inMatch ? 'none' : 'block');

        // Update games played counter
        this.svg.selectAll('.player .games-played')
            .text(d => d.gamesPlayed);
    }

    generateMatch() {
        const availablePlayers = this.players.filter(p => !p.inMatch && !this.pendingMatches.some(m => m.players.includes(p)));
        if (availablePlayers.length < 4) return false;

        const males = availablePlayers.filter(p => p.gender === 'M');
        const females = availablePlayers.filter(p => p.gender === 'F');

        // Determine match generation order based on last match type
        const lastMatch = [...this.matches, ...this.pendingMatches].slice(-1)[0];
        const lastType = lastMatch ? lastMatch.type : null;
        
        let matchTypes = [];
        if (lastType === "Mixed") {
            matchTypes = ["Mens", "Womens", "Mixed"];
        } else if (lastType === "Mens") {
            matchTypes = ["Womens", "Mixed", "Mens"];
        } else {
            matchTypes = ["Mixed", "Mens", "Womens"];
        }

        // Try to generate matches in the determined order
        for (const matchType of matchTypes) {
            if (matchType === "Mixed" && males.length >= 2 && females.length >= 2) {
                const maleCombos = this.getCombinations(males, 2);
                const bestMales = this.getBestCombination(maleCombos);
                
                const femaleCombos = this.getCombinations(females, 2);
                const bestFemales = this.getBestCombination(femaleCombos);
                
                if (bestMales && bestFemales) {
                    const players = [...bestMales, ...bestFemales];
                    this.pendingMatches.push({
                        players: players,
                        duration: this.matchDuration,
                        type: "Mixed"
                    });
                    players.forEach(p => p.inMatch = true);
                    return true;
                }
            } else if (matchType === "Mens" && males.length >= 4) {
                const maleCombos = this.getCombinations(males, 4);
                const bestMales = this.getBestCombination(maleCombos);
                
                if (bestMales) {
                    this.pendingMatches.push({
                        players: bestMales,
                        duration: this.matchDuration,
                        type: "Mens"
                    });
                    bestMales.forEach(p => p.inMatch = true);
                    return true;
                }
            } else if (matchType === "Womens" && females.length >= 4) {
                const femaleCombos = this.getCombinations(females, 4);
                const bestFemales = this.getBestCombination(femaleCombos);
                
                if (bestFemales) {
                    this.pendingMatches.push({
                        players: bestFemales,
                        duration: this.matchDuration,
                        type: "Womens"
                    });
                    bestFemales.forEach(p => p.inMatch = true);
                    return true;
                }
            }
        }
        return false;
    }

    getCombinations(players, count) {
        const results = [];
        if (count === 0) {
            return [[]];
        }
        if (players.length < count) {
            return [];
        }
        
        const firstPlayer = players[0];
        const rest = players.slice(1);
        
        // Get combinations that include the first player
        const combosWithFirst = this.getCombinations(rest, count - 1).map(combo => [firstPlayer, ...combo]);
        
        // Get combinations that don't include the first player
        const combosWithoutFirst = this.getCombinations(rest, count);
        
        return [...combosWithFirst, ...combosWithoutFirst];
    }

    getBestCombination(combinations) {
        if (combinations.length === 0) return null;
        
        let bestScore = Number.NEGATIVE_INFINITY;
        let bestCombo = null;
        
        for (const combo of combinations) {
            const score = this.scoreCombination(combo);
            if (score > bestScore) {
                bestScore = score;
                bestCombo = combo;
            }
        }
        
        return bestCombo;
    }

    scoreCombination(players) {
        let score = 0;
        
        // Factor 1: Wait time priority
        const waitTimes = players.map(p => p.waitTime);
        const maxWaitTime = Math.max(...waitTimes);
        score += maxWaitTime * 3;
        
        // Factor 2: Match count balancing
        const gamesPlayed = players.map(p => p.gamesPlayed);
        score -= Math.max(...gamesPlayed) * 2;
        
        // Factor 3: Player interaction history (simplified for visualization)
        // In a real system, we would track who has played with/against whom
        
        return score;
    }

    assignPlayersToMatch(players, court, matchType) {
        // Position players on court
        const positions = [
            { x: court.x + 45, y: court.y + 60 },
            { x: court.x + 45, y: court.y + 180 },
            { x: court.x + 135, y: court.y + 60 },
            { x: court.x + 135, y: court.y + 180 }
        ];

        players.forEach((player, i) => {
            player.x = positions[i].x;
            player.y = positions[i].y;
            player.inMatch = true;
            player.waitTime = 0;
            player.gamesPlayed += 1; // Increment games played when assigned to court
        });

        court.players = players;
    }

    updateMatches() {
        // End matches that are complete
        this.matches = this.matches.filter(match => {
            if (this.timeElapsed - match.startTime >= match.duration) {
                // Just mark players as not in match and clear court
                match.players.forEach(p => {
                    p.inMatch = false;
                });
                // Clear court
                this.courts[match.court].players = [];
                this.positionWaitingPlayers();
                return false;
            }
            return true;
        });

        // Try to assign pending matches to available courts
        const availableCourts = this.courts.filter(c => c.players.length === 0);
        while (availableCourts.length > 0 && this.pendingMatches.length > 0) {
            const court = availableCourts.shift();
            const match = this.pendingMatches.shift();
            this.assignPlayersToMatch(match.players, court, match.type);
            match.court = court.id;
            match.startTime = this.timeElapsed;
            this.matches.push(match);
        }

        // Generate new matches if needed
        const availableCourtCount = this.courts.filter(c => c.players.length === 0).length;
        if (availableCourtCount > 0 && this.pendingMatches.length < 3) {
            // Generate up to 3 matches based on match generation logic
            this.generateMatch();
        }
    }

    updateWaitTimes() {
        this.players.forEach(player => {
            if (!player.inMatch) {
                player.waitTime += 1;
            }
        });
    }

    updateStats() {
        const stats = document.getElementById('currentStats');
        const waitingPlayers = this.players.filter(p => !p.inMatch);
        const malesWaiting = waitingPlayers.filter(p => p.gender === 'M').length;
        const femalesWaiting = waitingPlayers.filter(p => p.gender === 'F').length;
        
        stats.innerHTML = `
            <p>Time: ${Math.floor(this.timeElapsed / 60)}h ${this.timeElapsed % 60}m</p>
            <p>Players Waiting: ${waitingPlayers.length}</p>
            <p>- Males: ${malesWaiting}</p>
            <p>- Females: ${femalesWaiting}</p>
            <p>Active Matches: ${this.matches.length}</p>
            <p>Pending Matches: ${this.pendingMatches.length}</p>
        `;
    }

    updateSimulation() {
        this.updateMatches();
        this.updatePlayerVisuals();
        this.updateStats();
        
        // Update slider if running automatically
        if (this.isRunning) {
            document.getElementById('timeSlider').noUiSlider.set(this.timeElapsed);
        }
    }

    start() {
        if (!this.isRunning) {
            this.isRunning = true;
            if (this.simulationTimer) {
                clearTimeout(this.simulationTimer);
                this.simulationTimer = null;
            }
            // Generate initial matches after a short delay to show the initial state
            setTimeout(() => {
                this.generateMatch();
                this.updateSimulation();
                this.simulationLoop();
            }, 1000);
        }
    }

    pause() {
        this.isRunning = false;
        if (this.simulationTimer) {
            clearTimeout(this.simulationTimer);
            this.simulationTimer = null;
        }
    }

    reset() {
        // Stop any running simulation and clear timer
        this.isRunning = false;
        if (this.simulationTimer) {
            clearTimeout(this.simulationTimer);
            this.simulationTimer = null;
        }
        
        // Clear all timers and state
        this.timeElapsed = 0;
        this.matches = [];
        this.pendingMatches = [];
        
        // Clear all court assignments
        this.courts.forEach(court => court.players = []);
        
        // Clear all D3 elements
        this.svg.selectAll('.player').remove();
        this.svg.selectAll('.wait-time').remove();
        
        // Reset the slider
        const slider = document.getElementById('timeSlider');
        if (slider && slider.noUiSlider) {
            slider.noUiSlider.set(0);
        }
        
        // Clear stats
        const stats = document.getElementById('currentStats');
        if (stats) {
            stats.innerHTML = '';
        }
        
        // Initialize new players
        this.players = [];
        this.initializePlayers();
        
        // Update the visualization with all players in waiting area
        this.positionWaitingPlayers(true);
        this.updateSimulation();
    }

    simulationLoop() {
        if (!this.isRunning || this.timeElapsed >= this.totalDuration) {
            this.isRunning = false;
            if (this.simulationTimer) {
                clearTimeout(this.simulationTimer);
                this.simulationTimer = null;
            }
            return;
        }

        this.timeElapsed += 1;
        this.updateWaitTimes();
        this.updateSimulation();

        this.simulationTimer = setTimeout(() => this.simulationLoop(), 1000); // Store timer reference
    }
}

// Initialize simulation when page loads
window.addEventListener('load', () => {
    const simulation = new PickleballSimulation();
    simulation.reset();
});
