// Matter.js module aliases
const { Engine, World, Bodies, Body, Runner } = Matter;

// Constants
const PLAYER_RADIUS = 15;
const COURT_WIDTH = 200;
const COURT_HEIGHT = 150;
const COURT_SPACING = 50;
const THOROUGHFARE_HEIGHT = 100;
const CANVAS_WIDTH = 1200;
const CANVAS_HEIGHT = 800;
const WAITING_AREA_WIDTH = CANVAS_WIDTH * 0.3;
const NUM_COURTS = 6;
const TOTAL_PLAYERS = 38;

// Add debug constants
const TOP_THOROUGHFARE_Y = THOROUGHFARE_HEIGHT;
const BOTTOM_THOROUGHFARE_Y = CANVAS_HEIGHT - THOROUGHFARE_HEIGHT;
const COURT_START_Y = THOROUGHFARE_HEIGHT * 2; // Start courts after top thoroughfare

// Matter.js setup
let engine = null;
let runner = null;

// Initialize Matter.js engine
function initEngine() {
    if (engine) {
        Matter.World.clear(engine.world);
        Matter.Engine.clear(engine);
    }
    
    engine = Engine.create({
        enableSleeping: false,
        constraintIterations: 4,
        velocityIterations: 8,
        positionIterations: 6
    });
    
    engine.world.gravity.y = 0;
    
    if (runner) {
        Matter.Runner.stop(runner);
    }
    
    runner = Runner.create({
        isFixed: true,
        delta: 1000 / 60
    });
    
    logDebugInfo('Engine Initialized', {
        engine: {
            world: engine.world !== null,
            gravity: engine.world.gravity,
            timing: engine.timing
        },
        runner: {
            isFixed: runner.isFixed,
            delta: runner.delta
        }
    });
    
    return engine;
}

// Debug info
let debugInfo = {
    playerStates: {},
    courtInfo: [],
    waitingPlayers: 0,
    thoroughfarePositions: [],
    errors: [],
    courtAssignments: []
};

function logDebugInfo(message, data) {
    console.log(`[DEBUG] ${message}:`, JSON.stringify(data, null, 2));
}

// Canvas setup
const canvas = document.getElementById('simulationCanvas');
const ctx = canvas.getContext('2d');

// Set canvas size
canvas.width = CANVAS_WIDTH;
canvas.height = CANVAS_HEIGHT;

// Global variables
let players = [];
let courts = [];
let matches = [];
let currentTime = 0;
let isPlaying = false;
let simulationSpeed = 1000; // 1 second = 1 minute
let matchDuration = 17.5; // minutes
let changeover = 5; // minutes
let gameLoopStarted = false;

class Player {
    constructor(id, gender) {
        this.id = id;
        this.gender = gender;
        this.gridPosition = null;
        this.state = 'waiting';
        this.targetX = null;
        this.targetY = null;
        this.currentCourt = null;
        this.courtPosition = null;
        this.movementQueue = null;
        this.matchStartTime = null;
        this.lastError = null;
        this.waypoints = null;
        this.moveDelay = Math.random() * 0.5; // Random delay up to 0.5 seconds
        this.speed = 1.5 + Math.random() * 1.5; // Random speed between 1.5 and 3
        
        // Create physics body
        this.body = Bodies.circle(0, 0, PLAYER_RADIUS, {
            friction: 0.001,
            frictionAir: 0.001,
            restitution: 0.1,
            inertia: Infinity,
            density: 0.001,
            isStatic: false,
            label: `player_${id}`
        });
        
        if (engine && engine.world) {
            World.add(engine.world, this.body);
        }
        
        // Log player creation
        logDebugInfo(`Created Player ${id}`, {
            gender,
            initialState: this.state,
            position: this.body.position
        });
    }
    
    getDebugInfo() {
        return {
            id: this.id,
            state: this.state,
            position: this.body.position,
            target: this.targetX !== null ? { x: this.targetX, y: this.targetY } : null,
            currentCourt: this.currentCourt ? this.currentCourt.index + 1 : null,
            movementQueue: this.movementQueue,
            lastError: this.lastError
        };
    }

    remove() {
        if (this.body && engine && engine.world) {
            World.remove(engine.world, this.body);
        }
    }

    assignGridPosition() {
        // Get current waiting players
        const waitingPlayers = players
            .filter(p => p.state === 'waiting' || p.state === 'returning')
            .sort((a, b) => a.id - b.id);
        
        // Find this player's position in the waiting list
        const index = waitingPlayers.findIndex(p => p.id === this.id);
        if (index === -1) return;
        
        // Calculate grid position
        const GRID_COLS = 6;
        const SPACING = PLAYER_RADIUS * 3;
        const col = index % GRID_COLS;
        const row = Math.floor(index / GRID_COLS);
        
        // Calculate actual coordinates
        this.gridPosition = {
            x: PLAYER_RADIUS * 2 + col * SPACING,
            y: PLAYER_RADIUS * 2 + row * SPACING
        };
    }

    returnToWaitingArea() {
        // Don't return if already returning or waiting
        if (this.state === 'returning' || this.state === 'waiting') return;
        
        this.state = 'returning';
        this.currentCourt = null;
        this.courtPosition = null;
        
        // Calculate thoroughfare path
        const currentY = this.body.position.y;
        const thoroughfareY = currentY < CANVAS_HEIGHT / 2 ? 
            THOROUGHFARE_HEIGHT : CANVAS_HEIGHT - THOROUGHFARE_HEIGHT;
        
        // Set up movement queue
        this.movementQueue = [
            { x: this.body.position.x, y: thoroughfareY }, // First move vertically to thoroughfare
            { x: WAITING_AREA_WIDTH + 30, y: thoroughfareY }, // Then move along thoroughfare
            null // Final position will be set when previous movements complete
        ];
        
        // Start first movement
        this.startNextMovement();
    }

    startNextMovement() {
        if (!this.movementQueue || this.movementQueue.length === 0) return;
        
        const nextPos = this.movementQueue[0];
        if (nextPos === null) {
            // Time to calculate grid position
            this.assignGridPosition();
            this.movementQueue[0] = this.gridPosition;
        }
        
        this.moveTo(this.movementQueue[0].x, this.movementQueue[0].y);
    }

    moveTo(x, y) {
        this.targetX = x;
        this.targetY = y;
    }

    update() {
        if (this.targetX !== null && this.targetY !== null) {
            const dx = this.targetX - this.body.position.x;
            const dy = this.targetY - this.body.position.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance > 1) {
                const speed = 3;
                const vx = (dx / distance) * speed;
                const vy = (dy / distance) * speed;
                Body.setVelocity(this.body, { x: vx, y: vy });
            } else {
                Body.setVelocity(this.body, { x: 0, y: 0 });
                
                // Handle movement queue
                if (this.movementQueue && this.movementQueue.length > 0) {
                    this.movementQueue.shift();
                    if (this.movementQueue.length > 0) {
                        this.startNextMovement();
                    } else {
                        // Movement complete
                        if (this.state === 'returning') {
                            this.state = 'waiting';
                        } else if (this.state === 'moving_to_court') {
                            this.state = 'playing';
                            this.matchStartTime = currentTime;
                        }
                        this.targetX = null;
                        this.targetY = null;
                    }
                } else {
                    this.targetX = null;
                    this.targetY = null;
                }
            }
        }
        
        // Maintain grid position if waiting
        if (this.state === 'waiting') {
            this.assignGridPosition();
            if (this.gridPosition) {
                const dx = this.gridPosition.x - this.body.position.x;
                const dy = this.gridPosition.y - this.body.position.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance > 1) {
                    const speed = 2;
                    const vx = (dx / distance) * speed;
                    const vy = (dy / distance) * speed;
                    Body.setVelocity(this.body, { x: vx, y: vy });
                }
            }
        }
    }

    draw() {
        const pos = this.body.position;
        
        // Draw player circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, PLAYER_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = this.gender === 'M' ? '#4444FF' : '#FF44FF';
        ctx.fill();
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw player number
        ctx.fillStyle = '#FFF';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(this.id.substring(1), pos.x, pos.y);
    }
}

class Court {
    constructor(index) {
        this.index = index;
        this.x = WAITING_AREA_WIDTH + COURT_SPACING + (COURT_WIDTH + COURT_SPACING) * (index % 3);
        this.y = COURT_START_Y + Math.floor(index / 3) * (COURT_HEIGHT + COURT_SPACING * 2);
        this.width = COURT_WIDTH;
        this.height = COURT_HEIGHT;
        this.currentMatch = null;
        this.positions = [
            {x: this.x + this.width * 0.25, y: this.y + this.height * 0.25},  // Top left
            {x: this.x + this.width * 0.25, y: this.y + this.height * 0.75},  // Bottom left
            {x: this.x + this.width * 0.75, y: this.y + this.height * 0.25},  // Top right
            {x: this.x + this.width * 0.75, y: this.y + this.height * 0.75}   // Bottom right
        ];
    }
    
    getDebugInfo() {
        const courtPlayers = players.filter(p => p.currentCourt === this);
        return {
            courtNumber: this.index + 1,
            position: { x: this.x, y: this.y },
            playerCount: courtPlayers.length,
            playerStates: courtPlayers.map(p => ({
                id: p.id,
                state: p.state,
                position: p.body.position,
                target: p.targetX !== null ? { x: p.targetX, y: p.targetY } : null
            })),
            isMatchReady: this.isMatchReady()
        };
    }

    isMatchReady() {
        const courtPlayers = players.filter(p => p.currentCourt === this && p.state === 'playing');
        if (courtPlayers.length !== 4) return false;
        
        // All players must be in 'playing' state
        return courtPlayers.every(p => p.state === 'playing');
    }
    
    draw() {
        const isReady = this.isMatchReady();
        logDebugInfo(`Court ${this.index + 1} Status`, {
            isReady,
            playerCount: players.filter(p => p.currentCourt === this).length,
            playerStates: players
                .filter(p => p.currentCourt === this)
                .map(p => ({ id: p.id, state: p.state }))
        });
        
        // Draw court background
        ctx.fillStyle = isReady ? '#90EE90' : '#FFB6C1';
        ctx.fillRect(this.x, this.y, this.width, this.height);
        
        // Draw court border
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.strokeRect(this.x, this.y, this.width, this.height);
        
        // Draw court number and player count
        const courtPlayers = players.filter(p => p.currentCourt === this);
        ctx.fillStyle = '#000';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`Court ${this.index + 1} (${courtPlayers.length}/4)`, 
                    this.x + this.width/2, 
                    this.y - 5);

        // Draw court positions
        this.positions.forEach((pos, idx) => {
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = '#666';
            ctx.fill();
        });
    }
}

function assignPlayersToMatch(players, court) {
    const positions = court.positions;
    players.forEach((player, index) => {
        player.state = 'moving_to_court';
        player.currentCourt = court;
        player.courtPosition = index;
        
        // Calculate path through nearest thoroughfare
        const thoroughfareY = court.index < 3 ? 
            THOROUGHFARE_HEIGHT : CANVAS_HEIGHT - THOROUGHFARE_HEIGHT;
        
        // First move to thoroughfare
        const entryPoint = {
            x: WAITING_AREA_WIDTH + 30,
            y: thoroughfareY
        };
        
        // Move to thoroughfare first
        player.moveTo(entryPoint.x, entryPoint.y);
        
        // Set timeout to move to final court position
        setTimeout(() => {
            player.moveTo(positions[index].x, positions[index].y);
        }, 2000);
    });
}

function movePlayerToTarget(player, targetX, targetY) {
    // Check move delay
    if (player.moveDelay > 0) {
        player.moveDelay -= 1/60; // Decrease delay each frame
        return false;
    }

    // Make sure body is dynamic
    if (player.body.isStatic) {
        Matter.Body.setStatic(player.body, false);
    }
    
    // Initialize waypoints if not exists
    if (!player.waypoints) {
        player.waypoints = calculatePathToTarget(player, targetX, targetY);
    }
    
    // Get next waypoint
    const nextWaypoint = findNextWaypoint(player);
    if (!nextWaypoint) {
        // No more waypoints, snap to final position
        Matter.Body.setPosition(player.body, { x: targetX, y: targetY });
        Matter.Body.setVelocity(player.body, { x: 0, y: 0 });
        Matter.Body.setAngularVelocity(player.body, 0);
        Matter.Body.setStatic(player.body, true);
        player.waypoints = null;
        return true;
    }
    
    // Check for nearby players in the direction of movement
    const dx = nextWaypoint.x - player.body.position.x;
    const dy = nextWaypoint.y - player.body.position.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    // Check if path is blocked
    const isBlocked = players.some(other => {
        if (other === player || other.state === 'playing') return false;
        
        const odx = other.body.position.x - player.body.position.x;
        const ody = other.body.position.y - player.body.position.y;
        const otherDistance = Math.sqrt(odx * odx + ody * ody);
        
        // Check if other player is close and in our path
        if (otherDistance < PLAYER_RADIUS * 4) {
            const dotProduct = (dx * odx + dy * ody) / (distance * otherDistance);
            return dotProduct > 0.7; // Player is roughly in our direction
        }
        return false;
    });
    
    if (isBlocked) {
        // Stop and wait but stay dynamic
        Matter.Body.setVelocity(player.body, { x: 0, y: 0 });
        return false;
    }
    
    // Move towards next waypoint with player's unique speed
    const speed = player.speed;
    const vx = (dx / distance) * speed;
    const vy = (dy / distance) * speed;
    
    // Update velocity and ensure body is awake
    Matter.Body.setVelocity(player.body, { x: vx, y: vy });
    Matter.Body.setAngularVelocity(player.body, 0);
    Matter.Sleeping.set(player.body, false);
    
    // Draw path for debugging
    if (DEBUG) {
        ctx.beginPath();
        ctx.moveTo(player.body.position.x, player.body.position.y);
        player.waypoints.forEach(waypoint => {
            ctx.lineTo(waypoint.x, waypoint.y);
        });
        ctx.strokeStyle = '#0f0';
        ctx.stroke();
    }
    
    return false;
}

function initializePlayer(id, gender) {
    const radius = PLAYER_RADIUS;
    const body = Bodies.circle(0, 0, radius, {
        friction: 0.001,
        frictionAir: 0.001,
        restitution: 0.1,
        inertia: Infinity,
        density: 0.001,
        isStatic: false,
        label: `player_${id}`
    });
    
    const player = {
        id,
        body,
        gender,
        state: 'waiting',
        currentCourt: null,
        courtPosition: null,
        targetX: null,
        targetY: null,
        matchStartTime: null,
        waypoints: null,
        moveDelay: Math.random() * 0.5,
        speed: 1.5 + Math.random() * 1.5
    };
    
    // Make sure body references player
    body.plugin = { player };
    
    return player;
}

function calculatePathToTarget(player, targetX, targetY) {
    const waypoints = [];
    const currentPos = player.body.position;
    
    // If player is in waiting area and needs to go to court
    if (player.state === 'moving_to_court' && player.currentCourt) {
        // First move to thoroughfare entrance
        const thoroughfareY = player.currentCourt.index < 3 ? 
            TOP_THOROUGHFARE_Y + THOROUGHFARE_HEIGHT/2 : 
            BOTTOM_THOROUGHFARE_Y + THOROUGHFARE_HEIGHT/2;
            
        // Add waypoint at waiting area exit
        waypoints.push({
            x: WAITING_AREA_WIDTH - PLAYER_RADIUS * 2,
            y: currentPos.y
        });
        
        // Add waypoint at thoroughfare entrance
        waypoints.push({
            x: WAITING_AREA_WIDTH + PLAYER_RADIUS * 2,
            y: thoroughfareY
        });
        
        // Add waypoint in front of court
        waypoints.push({
            x: player.currentCourt.x - PLAYER_RADIUS * 2,
            y: thoroughfareY
        });
    }
    
    // Add final target
    waypoints.push({ x: targetX, y: targetY });
    
    return waypoints;
}

function findNextWaypoint(player) {
    if (!player.waypoints || player.waypoints.length === 0) {
        // Calculate new path to target
        if (player.targetX !== null && player.targetY !== null) {
            player.waypoints = calculatePathToTarget(player, player.targetX, player.targetY);
        }
        return null;
    }
    
    // Check if we've reached current waypoint
    const currentWaypoint = player.waypoints[0];
    const dx = currentWaypoint.x - player.body.position.x;
    const dy = currentWaypoint.y - player.body.position.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    if (distance < 1) {
        // Remove reached waypoint
        player.waypoints.shift();
        return player.waypoints[0] || null;
    }
    
    return currentWaypoint;
}

function assignPlayersToAvailableCourts() {
    const availableCourts = courts
        .filter(court => !court.currentMatch && !players.some(p => p.currentCourt === court))
        .sort((a, b) => a.index - b.index);
        
    const waitingPlayers = players
        .filter(p => p.state === 'waiting' && !p.currentCourt)
        .sort((a, b) => a.id - b.id);
    
    logDebugInfo('Court Assignment Check', {
        availableCourts: availableCourts.map(c => c.index + 1),
        waitingPlayerCount: waitingPlayers.length,
        currentTime
    });
    
    // Assign players with delays
    availableCourts.forEach(court => {
        if (waitingPlayers.length >= 4) {
            const playersForCourt = waitingPlayers.splice(0, 4);
            
            // Add random delays to stagger movement
            playersForCourt.forEach((player, idx) => {
                player.moveDelay = idx * 0.2 + Math.random() * 0.3; // Stagger starts plus random offset
            });
            
            // Assign players to court
            playersForCourt.forEach((player, idx) => {
                player.state = 'moving_to_court';
                player.currentCourt = court;
                player.courtPosition = idx;
                const pos = court.positions[idx];
                player.targetX = pos.x;
                player.targetY = pos.y;
            });
            
            // Initialize match
            court.currentMatch = {
                startTime: currentTime,
                players: playersForCourt.map(p => p.id)
            };
        }
    });
}

function updateSimulation() {
    // Reset debug info
    debugInfo = {
        playerStates: {},
        courtInfo: [],
        waitingPlayers: 0,
        thoroughfarePositions: [],
        errors: [],
        courtAssignments: []
    };
    
    try {
        // First, check for available courts and waiting players
        assignPlayersToAvailableCourts();
        
        // Update all players
        players.forEach(player => {
            try {
                switch (player.state) {
                    case 'waiting':
                        if (!player.currentCourt) {
                            const waitingIndex = players
                                .filter(p => p.state === 'waiting' && !p.currentCourt)
                                .sort((a, b) => a.id - b.id)
                                .findIndex(p => p.id === player.id);
                                
                            if (waitingIndex !== -1) {
                                const col = Math.floor(waitingIndex / 6);
                                const row = waitingIndex % 6;
                                const targetX = col * (PLAYER_RADIUS * 3) + PLAYER_RADIUS * 2;
                                const targetY = row * (PLAYER_RADIUS * 3) + PLAYER_RADIUS * 2;
                                movePlayerToTarget(player, targetX, targetY);
                            }
                        }
                        break;
                        
                    case 'moving_to_court':
                        if (player.targetX !== null && player.targetY !== null) {
                            const arrived = movePlayerToTarget(player, player.targetX, player.targetY);
                            if (arrived) {
                                player.state = 'playing';
                                player.matchStartTime = currentTime;
                                
                                // Ensure player is static and exactly at position
                                const pos = player.currentCourt.positions[player.courtPosition];
                                Matter.Body.setPosition(player.body, pos);
                                Matter.Body.setStatic(player.body, true);
                                
                                logDebugInfo('Player Arrived at Court', {
                                    playerId: player.id,
                                    courtNumber: player.currentCourt.index + 1,
                                    position: player.courtPosition,
                                    time: currentTime
                                });
                            }
                        }
                        break;
                        
                    case 'playing':
                        // Ensure player stays exactly at their position
                        const pos = player.currentCourt.positions[player.courtPosition];
                        Matter.Body.setPosition(player.body, pos);
                        Matter.Body.setStatic(player.body, true);
                        
                        if (player.matchStartTime && (currentTime - player.matchStartTime) >= matchDuration * 60) {
                            player.state = 'returning';
                            player.targetX = WAITING_AREA_WIDTH / 2;
                            player.targetY = CANVAS_HEIGHT - THOROUGHFARE_HEIGHT / 2;
                            player.currentCourt.currentMatch = null;
                            player.matchStartTime = null;
                            Matter.Body.setStatic(player.body, false);
                        }
                        break;
                        
                    case 'returning':
                        if (player.targetX !== null && player.targetY !== null) {
                            const arrived = movePlayerToTarget(player, player.targetX, player.targetY);
                            if (arrived) {
                                player.state = 'waiting';
                                player.currentCourt = null;
                                player.courtPosition = null;
                                player.targetX = null;
                                player.targetY = null;
                                Matter.Body.setStatic(player.body, true);
                            }
                        }
                        break;
                }
                
                // Track player states
                debugInfo.playerStates[player.state] = (debugInfo.playerStates[player.state] || 0) + 1;
                
                // Track thoroughfare positions
                if (player.state === 'moving_to_court' || player.state === 'returning') {
                    debugInfo.thoroughfarePositions.push({
                        id: player.id,
                        position: player.body.position,
                        state: player.state
                    });
                }
            } catch (error) {
                debugInfo.errors.push({
                    playerId: player.id,
                    error: error.message,
                    stack: error.stack,
                    state: player.state,
                    position: player.body ? player.body.position : null
                });
            }
        });
        
        // Update court info for debugging
        courts.forEach(court => {
            debugInfo.courtInfo.push({
                ...court.getDebugInfo(),
                assignedPlayers: players
                    .filter(p => p.currentCourt === court)
                    .map(p => ({
                        id: p.id,
                        state: p.state,
                        position: p.courtPosition
                    }))
            });
        });
        
        // Count waiting players
        debugInfo.waitingPlayers = players.filter(p => p.state === 'waiting' && !p.currentCourt).length;
        
    } catch (error) {
        debugInfo.errors.push({
            error: error.message,
            stack: error.stack,
            phase: 'main_update'
        });
    }
    
    // Log debug info every second
    if (Math.floor(currentTime) !== Math.floor(currentTime - 1/60)) {
        logDebugInfo('Simulation State', debugInfo);
    }
}

function draw() {
    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Log render cycle
    logDebugInfo('Render Cycle', {
        time: currentTime,
        canvasSize: { width: canvas.width, height: canvas.height },
        activePlayerCount: players.length,
        activeCourts: courts.length
    });

    try {
        // Draw waiting area background
        ctx.fillStyle = '#f0f0f0';
        ctx.fillRect(0, 0, WAITING_AREA_WIDTH, canvas.height);

        // Draw thoroughfares
        ctx.fillStyle = '#e0e0e0';
        ctx.fillRect(0, 0, canvas.width, THOROUGHFARE_HEIGHT); // Top thoroughfare
        ctx.fillRect(0, canvas.height - THOROUGHFARE_HEIGHT, canvas.width, THOROUGHFARE_HEIGHT); // Bottom thoroughfare

        // Draw courts with debug info
        courts.forEach(court => {
            // Draw court background
            const courtPlayers = players.filter(p => p.currentCourt === court);
            ctx.fillStyle = court.isMatchReady() ? '#90EE90' : '#FFB6C1';
            ctx.fillRect(court.x, court.y, court.width, court.height);
            
            // Draw court border
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 2;
            ctx.strokeRect(court.x, court.y, court.width, court.height);
            
            // Draw court number and player count
            ctx.fillStyle = '#000';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(`Court ${court.index + 1} (${courtPlayers.length}/4)`, 
                        court.x + court.width/2, 
                        court.y - 5);

            // Draw court positions
            court.positions.forEach((pos, idx) => {
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, 5, 0, Math.PI * 2);
                ctx.fillStyle = '#666';
                ctx.fill();
            });
        });

        // Draw all players
        players.forEach(player => {
            if (!player || !player.body) {
                logDebugInfo('Invalid Player', { player });
                return;
            }

            try {
                ctx.beginPath();
                ctx.arc(player.body.position.x, player.body.position.y, PLAYER_RADIUS, 0, Math.PI * 2);
                ctx.fillStyle = player.gender === 'M' ? '#4169E1' : '#FF69B4';
                ctx.fill();
                ctx.strokeStyle = '#000';
                ctx.lineWidth = 1;
                ctx.stroke();

                // Draw player ID
                ctx.fillStyle = '#000';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(player.id.toString(), player.body.position.x, player.body.position.y);

                // Draw debug line to target if moving
                if (player.targetX !== null && player.targetY !== null) {
                    ctx.beginPath();
                    ctx.moveTo(player.body.position.x, player.body.position.y);
                    ctx.lineTo(player.targetX, player.targetY);
                    ctx.strokeStyle = '#00ff00';
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            } catch (error) {
                logDebugInfo('Player Render Error', {
                    playerId: player.id,
                    error: error.message,
                    position: player.body.position,
                    state: player.state
                });
            }
        });

        // Request next frame
        requestAnimationFrame(gameLoop);
    } catch (error) {
        logDebugInfo('Main Render Error', {
            error: error.message,
            stack: error.stack
        });
        // Still request next frame even if there's an error
        requestAnimationFrame(gameLoop);
    }
}

function updateTimeDisplay() {
    const minutes = Math.floor(currentTime / 60);
    const seconds = Math.floor(currentTime % 60);
    const timeDisplay = document.getElementById('timeDisplay');
    if (timeDisplay) {
        timeDisplay.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    
    const timeSlider = document.getElementById('timeSlider');
    if (timeSlider) {
        timeSlider.value = currentTime;
    }
}

function gameLoop() {
    const now = performance.now();
    const deltaTime = 1/60; // Fixed time step
    currentTime += deltaTime;
    
    try {
        Engine.update(engine, 1000 * deltaTime);
        updateSimulation();
        draw();
        
        // Update time display
        updateTimeDisplay();
        
    } catch (error) {
        logDebugInfo('Game Loop Error', {
            error: error.message,
            stack: error.stack,
            time: currentTime
        });
        // Ensure we keep running even if there's an error
        requestAnimationFrame(gameLoop);
    }
}

function initializeSimulation() {
    // Create engine and world
    engine = Engine.create({
        enableSleeping: false,
        constraintIterations: 4,
        velocityIterations: 8,
        positionIterations: 6
    });
    
    engine.world.gravity.y = 0;
    
    // Create players
    players = [];
    for (let i = 0; i < TOTAL_PLAYERS; i++) {
        const gender = i % 2 === 0 ? 'M' : 'F';
        const player = initializePlayer(i + 1, gender);
        const waitingPos = getWaitingPosition(i + 1);
        Matter.Body.setPosition(player.body, waitingPos);
        players.push(player);
        World.add(engine.world, player.body);
    }
    
    // Create courts
    courts = [];
    for (let i = 0; i < NUM_COURTS; i++) {
        courts.push(new Court(i));
    }
    
    // Initialize time
    startTime = Date.now();
    currentTime = 0;
    
    // Start game loop
    requestAnimationFrame(updateSimulation);
}

function updateSimulation() {
    // Reset debug info
    debugInfo = {
        courts: [],
        players: [],
        errors: []
    };

    // Update current time
    currentTime = (Date.now() - startTime) / 1000;
    
    // Assign waiting players to available courts
    assignPlayersToAvailableCourts();
    
    // Update player states and positions
    players.forEach(player => {
        try {
            updatePlayerState(player);
            
            // Log player state for debugging
            if (DEBUG) {
                console.log(`Player ${player.id}: state=${player.state}, pos=(${Math.round(player.body.position.x)}, ${Math.round(player.body.position.y)}), vel=(${Math.round(player.body.velocity.x*100)/100}, ${Math.round(player.body.velocity.y*100)/100}), static=${player.body.isStatic}`);
            }
        } catch (error) {
            player.lastError = error;
            debugInfo.errors.push(`Error updating player ${player.id}: ${error.message}`);
        }
    });

    // Update Matter.js physics
    Engine.update(engine, 1000/60);

    // Draw everything
    drawSimulation();
    
    // Continue game loop
    requestAnimationFrame(updateSimulation);
}

function drawSimulation() {
    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw waiting area background
    ctx.fillStyle = '#f0f0f0';
    ctx.fillRect(0, 0, WAITING_AREA_WIDTH, canvas.height);

    // Draw thoroughfares
    ctx.fillStyle = '#e0e0e0';
    ctx.fillRect(0, 0, canvas.width, THOROUGHFARE_HEIGHT); // Top thoroughfare
    ctx.fillRect(0, canvas.height - THOROUGHFARE_HEIGHT, canvas.width, THOROUGHFARE_HEIGHT); // Bottom thoroughfare

    // Draw courts with debug info
    courts.forEach(court => {
        // Draw court background
        const courtPlayers = players.filter(p => p.currentCourt === court);
        ctx.fillStyle = court.isMatchReady() ? '#90EE90' : '#FFB6C1';
        ctx.fillRect(court.x, court.y, court.width, court.height);
        
        // Draw court border
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.strokeRect(court.x, court.y, court.width, court.height);
        
        // Draw court number and player count
        ctx.fillStyle = '#000';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`Court ${court.index + 1} (${courtPlayers.length}/4)`, 
                    court.x + court.width/2, 
                    court.y - 5);

        // Draw court positions
        court.positions.forEach((pos, idx) => {
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = '#666';
            ctx.fill();
        });
    });

    // Draw all players
    players.forEach(player => {
        if (!player || !player.body) {
            logDebugInfo('Invalid Player', { player });
            return;
        }

        try {
            ctx.beginPath();
            ctx.arc(player.body.position.x, player.body.position.y, PLAYER_RADIUS, 0, Math.PI * 2);
            ctx.fillStyle = player.gender === 'M' ? '#4169E1' : '#FF69B4';
            ctx.fill();
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 1;
            ctx.stroke();

            // Draw player ID
            ctx.fillStyle = '#000';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(player.id.toString(), player.body.position.x, player.body.position.y);

            // Draw debug line to target if moving
            if (player.targetX !== null && player.targetY !== null) {
                ctx.beginPath();
                ctx.moveTo(player.body.position.x, player.body.position.y);
                ctx.lineTo(player.targetX, player.targetY);
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 1;
                ctx.stroke();
            }
        } catch (error) {
            logDebugInfo('Player Render Error', {
                playerId: player.id,
                error: error.message,
                position: player.body.position,
                state: player.state
            });
        }
    });
}

function updatePlayerState(player) {
    // Update player state based on current position and target
    if (player.targetX !== null && player.targetY !== null) {
        const dx = player.targetX - player.body.position.x;
        const dy = player.targetY - player.body.position.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance > 1) {
            const speed = 3;
            const vx = (dx / distance) * speed;
            const vy = (dy / distance) * speed;
            Matter.Body.setVelocity(player.body, { x: vx, y: vy });
        } else {
            Matter.Body.setVelocity(player.body, { x: 0, y: 0 });
            
            // Handle movement queue
            if (player.movementQueue && player.movementQueue.length > 0) {
                player.movementQueue.shift();
                if (player.movementQueue.length > 0) {
                    player.startNextMovement();
                } else {
                    // Movement complete
                    if (player.state === 'returning') {
                        player.state = 'waiting';
                    } else if (player.state === 'moving_to_court') {
                        player.state = 'playing';
                        player.matchStartTime = currentTime;
                    }
                    player.targetX = null;
                    player.targetY = null;
                }
            } else {
                player.targetX = null;
                player.targetY = null;
            }
        }
    }
    
    // Maintain grid position if waiting
    if (player.state === 'waiting') {
        player.assignGridPosition();
        if (player.gridPosition) {
            const dx = player.gridPosition.x - player.body.position.x;
            const dy = player.gridPosition.y - player.body.position.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance > 1) {
                const speed = 2;
                const vx = (dx / distance) * speed;
                const vy = (dy / distance) * speed;
                Matter.Body.setVelocity(player.body, { x: vx, y: vy });
            }
        }
    }
}

function getWaitingPosition(playerId) {
    const waitingIndex = playerId - 1;
    const col = Math.floor(waitingIndex / 6);
    const row = waitingIndex % 6;
    const x = col * (PLAYER_RADIUS * 3) + PLAYER_RADIUS * 2;
    const y = row * (PLAYER_RADIUS * 3) + PLAYER_RADIUS * 2;
    return { x, y };
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initialize UI elements if they exist
    const playerSelect = document.getElementById('playerCount');
    if (!playerSelect) {
        logDebugInfo('Warning: playerCount select not found, using default value');
    }
    
    const startButton = document.getElementById('startButton');
    if (startButton) {
        startButton.addEventListener('click', () => {
            initializeSimulation();
        });
    } else {
        logDebugInfo('Warning: startButton not found, simulation will start automatically');
        initializeSimulation();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (engine) {
        Matter.World.clear(engine.world);
        Matter.Engine.clear(engine);
    }
    if (runner) {
        Matter.Runner.stop(runner);
    }
    engine = null;
    runner = null;
    players = [];
    courts = [];
});
