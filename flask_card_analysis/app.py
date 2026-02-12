"""
Card Placement Analysis - Flask Web Application
Main Application File

"""

from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import io
import base64
from collections import Counter
import ast
import re
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

# Global variables
df = None
visualizer = None

class CardPlacementVisualizer:
    """
    Card placement visualizer adapted for Flask web application.
    Handles all visualization logic for card sorting trials.
    """
    
    def __init__(self, df, figure_size=(7, 7)):
        """
        Initialize the visualizer.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            The preprocessed card sorting dataset
        figure_size : tuple
            Figure dimensions (width, height) in inches
        """
        self.df = df
        self.grid_size = 8
        self.figure_size = figure_size
        
        # Card color scheme
        self.card_colors = {
            'queen': '#FF6B6B',    # Red
            'king': '#4ECDC4',     # Teal
            'jack': '#45B7D1',     # Blue
            'blank': '#95E1D3',    # Light Green
            'empty': '#F7F7F7'     # Light Gray
        }
        
        # Suit symbols
        self.suit_symbols = {
            'spades': '♠',
            'hearts': '♥',
            'diamonds': '♦',
            'clubs': '♣'
        }
    
    def parse_position(self, position_str):
        """
        Parse position string to grid coordinates.
        
        Parameters:
        -----------
        position_str : str
            Position in format 'A1', 'B3', etc. or 'Off Grid'
        
        Returns:
        --------
        tuple or None : (row, col) coordinates or None if off-grid
        """
        if pd.isna(position_str) or 'Off Grid' in str(position_str):
            return None
        
        try:
            position_str = str(position_str).strip()
            if len(position_str) >= 2:
                col_letter = position_str[0]
                row_num = position_str[1:]
                col = ord(col_letter.upper()) - ord('A')
                row = int(row_num) - 1
                
                if 0 <= row < self.grid_size and 0 <= col < self.grid_size:
                    return (row, col)
        except:
            pass
        return None
    
    def extract_card_info(self, move_str):
        """
        Extract card information from movement string.
        
        Parameters:
        -----------
        move_str : str
            Movement string like 'queen_spades_A1'
        
        Returns:
        --------
        dict or None : Card information dictionary
        """
        if pd.isna(move_str) or move_str == '':
            return None
        
        try:
            parts = str(move_str).split('_')
            if len(parts) >= 2:
                card_rank = parts[0]
                suit = parts[1] if len(parts) > 1 else ''
                position = parts[-1] if len(parts) > 2 else 'Off Grid'
                color = self.card_colors.get(card_rank.lower(), self.card_colors['empty'])
                
                return {
                    'rank': card_rank,
                    'suit': suit,
                    'position': position,
                    'color': color,
                    'symbol': self.suit_symbols.get(suit, '')
                }
        except:
            pass
        return None
    
    def create_grid_state(self, movements, step):
        """
        Create grid state at a specific step in the trial.
        
        Parameters:
        -----------
        movements : list
            List of movement strings
        step : int
            Step number (0 to len(movements))
        
        Returns:
        --------
        numpy.ndarray : Grid state with card information
        """
        grid = np.empty((self.grid_size, self.grid_size), dtype=object)
        card_positions = {}
        
        for i in range(min(step, len(movements))):
            card_info = self.extract_card_info(movements[i])
            if card_info:
                position_coords = self.parse_position(card_info['position'])
                card_key = f"{card_info['rank']}_{card_info['suit']}"
                
                # Remove card from previous position
                if card_key in card_positions:
                    old_row, old_col = card_positions[card_key]
                    if old_row is not None:
                        grid[old_row, old_col] = None
                
                # Place card at new position
                if position_coords:
                    row, col = position_coords
                    grid[row, col] = card_info
                    card_positions[card_key] = (row, col)
                else:
                    card_positions[card_key] = (None, None)
        
        return grid
    
    def plot_grid(self, grid, ax, step, total_steps, trial_info):
        """
        Plot the grid state on a matplotlib axis.
        Thread-safe implementation.
        
        Parameters:
        -----------
        grid : numpy.ndarray
            Current grid state
        ax : matplotlib.axes.Axes
            Axis to plot on
        step : int
            Current step number
        total_steps : int
            Total steps in trial
        trial_info : dict
            Trial metadata
        """
        from matplotlib.patches import Rectangle
        
        ax.clear()
        
        # Set white background
        ax.set_facecolor('white')
        
        # Create light gray background
        color_grid = np.zeros((self.grid_size, self.grid_size, 3))
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                color_grid[i, j] = [0.97, 0.97, 0.97]
        
        ax.imshow(color_grid, aspect='auto')
        
        # Draw gridlines
        for i in range(self.grid_size + 1):
            ax.axhline(i - 0.5, color='gray', linewidth=0.8, alpha=0.3)
            ax.axvline(i - 0.5, color='gray', linewidth=0.8, alpha=0.3)
        
        # Draw cards
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i, j] is not None:
                    card_info = grid[i, j]
                    
                    # Draw card rectangle
                    rect = Rectangle((j - 0.45, i - 0.45), 0.9, 0.9,
                                    facecolor=card_info['color'],
                                    edgecolor='black',
                                    linewidth=1.5,
                                    alpha=0.9)
                    ax.add_patch(rect)
                    
                    # Add rank text
                    rank_text = card_info['rank'][0].upper()
                    suit_symbol = card_info['symbol']
                    
                    ax.text(j, i - 0.1, rank_text, 
                           ha='center', va='center',
                           fontsize=12, fontweight='bold',
                           color='white')
                    
                    # Add suit symbol
                    if suit_symbol:
                        ax.text(j, i + 0.15, suit_symbol,
                               ha='center', va='center',
                               fontsize=10,
                               color='white')
        
        # Add row labels
        for i in range(self.grid_size):
            ax.text(-0.7, i, str(i + 1),
                   ha='center', va='center',
                   fontsize=9, fontweight='bold')
        
        # Add column labels
        for j in range(self.grid_size):
            ax.text(j, -0.7, chr(65 + j),
                   ha='center', va='center',
                   fontsize=9, fontweight='bold')
        
        # Set axis properties
        ax.set_xlim(-1, self.grid_size)
        ax.set_ylim(self.grid_size, -1)
        ax.axis('off')
        
        # Create title
        participant = trial_info.get('participant', 'N/A')
        trial_n = trial_info.get('trialN', 'N/A')
        condition = trial_info.get('condition', 'N/A')
        success = trial_info.get('overall_correct', 0)
        
        success_text = '✓ Success' if success == 1 else '✗ Failed'
        title_color = 'green' if success == 1 else 'red'
        
        title = f'Participant {participant} | Trial {trial_n} | Condition: {condition} | {success_text}\n'
        title += f'Step {step}/{total_steps}'
        
        ax.set_title(title, fontsize=11, fontweight='bold', pad=15,
                    color=title_color if step == total_steps else 'black')
    
    def generate_static_image(self, participant, trial_n, step=None):
        """
        Generate a static PNG image of the trial grid.
        Thread-safe implementation using Figure instead of global plt.
        
        Parameters:
        -----------
        participant : int
            Participant ID
        trial_n : int
            Trial number
        step : int, optional
            Specific step to show (default: final step)
        
        Returns:
        --------
        io.BytesIO : PNG image bytes
        """
        trial_data = self.df[(self.df['participant'] == participant) & 
                            (self.df['trialN'] == trial_n)]
        
        if trial_data.empty:
            return None
        
        trial_data = trial_data.iloc[0]
        movements = trial_data['movement_codes']
        
        if not movements:
            return None
        
        if step is None:
            step = len(movements)
        
        # Create isolated figure (thread-safe)
        fig = Figure(figsize=self.figure_size, facecolor='white')
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        
        trial_info = {
            'participant': participant,
            'trialN': trial_n,
            'condition': trial_data.get('condition', 'N/A'),
            'overall_correct': trial_data.get('overall_correct', 0)
        }
        
        grid = self.create_grid_state(movements, step)
        self.plot_grid(grid, ax, step, len(movements), trial_info)
        
        fig.tight_layout()
        
        # Save to bytes using canvas (thread-safe)
        img_bytes = io.BytesIO()
        canvas.print_png(img_bytes)
        img_bytes.seek(0)
        
        return img_bytes
    
    def generate_animation_html(self, participant, trial_n):
        """
        Generate HTML5 animation of the trial.
        Saves as separate file to avoid JavaScript scoping issues.
        
        Parameters:
        -----------
        participant : int
            Participant ID
        trial_n : int
            Trial number
        
        Returns:
        --------
        str : HTML content with embedded animation in iframe
        """
        trial_data = self.df[(self.df['participant'] == participant) & 
                            (self.df['trialN'] == trial_n)]
        
        if trial_data.empty:
            return None
        
        trial_data = trial_data.iloc[0]
        movements = trial_data['movement_codes']
        
        if not movements:
            return None
        
        # Create figure
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        trial_info = {
            'participant': participant,
            'trialN': trial_n,
            'condition': trial_data.get('condition', 'N/A'),
            'overall_correct': trial_data.get('overall_correct', 0)
        }
        
        total_steps = len(movements)
        
        def update(frame):
            grid = self.create_grid_state(movements, frame)
            self.plot_grid(grid, ax, frame, total_steps, trial_info)
            fig.tight_layout()
            return ax,
        
        # Create animation
        anim = FuncAnimation(fig, update, frames=total_steps + 1,
                           interval=500, repeat=True, blit=False)
        
        # Save animation to file
        anim_filename = f'animation_{participant}_{trial_n}.html'
        anim_path = os.path.join('static', 'animations', anim_filename)
        
        # Create animations directory if it doesn't exist
        os.makedirs(os.path.join('static', 'animations'), exist_ok=True)
        
        # Save animation
        with open(anim_path, 'w') as f:
            f.write(anim.to_jshtml())
        
        plt.close()
        
        # Return iframe pointing to the saved file
        return f'/static/animations/{anim_filename}'


# Data preprocessing functions
def safe_literal_eval(x):
    """Safely evaluate string representations of Python literals."""
    if pd.isna(x) or x == '' or x == '[]':
        return []
    try:
        return ast.literal_eval(x) if isinstance(x, str) else x
    except:
        return []

def clean_card_positions(movement_list):
    """Clean card position labels by removing extraneous characters."""
    if not isinstance(movement_list, list):
        return movement_list
    
    cleaned_list = []
    for move in movement_list:
        if not isinstance(move, str):
            cleaned_list.append(move)
            continue
        
        parts = move.split('_')
        
        # Remove lowercase prefix from last part
        if re.match(r'^[a-z]', parts[-1]):
            parts[-1] = parts[-1][1:]
        # Remove standalone 'c' in second-to-last position
        elif len(parts) >= 2 and parts[-2] == 'c':
            parts.pop(-2)
        
        cleaned_list.append("_".join(parts))
    
    return cleaned_list

def load_data():
    """Load and preprocess the dataset."""
    global df, visualizer
    
    data_path = 'data/CardsDataset.csv'
    if not os.path.exists(data_path):
        return False
    
    # Load CSV
    df = pd.read_csv(data_path)
    
    # Preprocess movement columns
    df['movement_codes'] = df['movement_codes'].apply(safe_literal_eval)
    df['movement_codes'] = df['movement_codes'].apply(clean_card_positions)
    df['final_card_position_codes_1'] = df['final_card_position_codes_1'].apply(safe_literal_eval)
    df['final_card_position_codes_1'] = df['final_card_position_codes_1'].apply(clean_card_positions)
    
    # Create visualizer
    visualizer = CardPlacementVisualizer(df)
    
    return True


# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Homepage with overview statistics."""
    if df is None:
        return render_template('error.html', 
                             message="Dataset not loaded. Please ensure CardsDataset.csv is in the data/ folder.")
    
    stats = {
        'total_trials': len(df),
        'unique_participants': df['participant'].nunique(),
        'success_trials': len(df[df['overall_correct'] == 1]),
        'failed_trials': len(df[df['overall_correct'] == 0]),
        'success_rate': (df['overall_correct'] == 1).mean() * 100,
        'avg_moves': df['movement_codes'].apply(len).mean(),
        'conditions': df['condition'].unique().tolist()
    }
    
    return render_template('index.html', stats=stats)


@app.route('/explorer')
def explorer():
    """Interactive trial explorer page."""
    if df is None:
        return render_template('error.html', message="Dataset not loaded")
    
    participants = sorted(df['participant'].unique().tolist())
    return render_template('explorer.html', participants=participants)


@app.route('/patterns')
def patterns():
    """Pattern analysis page."""
    if df is None:
        return render_template('error.html', message="Dataset not loaded")
    
    success_df = df[df['overall_correct'] == 1]
    failure_df = df[df['overall_correct'] == 0]
    
    return render_template('patterns.html', 
                         success_count=len(success_df),
                         failure_count=len(failure_df))


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/get-trials/<int:participant>')
def get_trials(participant):
    """Get all trials for a specific participant."""
    trials = df[df['participant'] == participant]['trialN'].unique().tolist()
    return jsonify(sorted(trials))


@app.route('/api/trial-info/<int:participant>/<int:trial_n>')
def trial_info(participant, trial_n):
    """Get detailed information about a specific trial."""
    trial_data = df[(df['participant'] == participant) & 
                   (df['trialN'] == trial_n)]
    
    if trial_data.empty:
        return jsonify({'error': 'Trial not found'}), 404
    
    trial = trial_data.iloc[0]
    
    return jsonify({
        'participant': int(participant),
        'trial': int(trial_n),
        'condition': str(trial['condition']),
        'success': bool(trial['overall_correct'] == 1),
        'total_moves': len(trial['movement_codes']),
        'movements': trial['movement_codes']
    })


@app.route('/api/generate-animation/<int:participant>/<int:trial_n>')
def generate_animation(participant, trial_n):
    """Generate animation and return file path."""
    anim_file = visualizer.generate_animation_html(participant, trial_n)
    
    if anim_file is None:
        return jsonify({'error': 'Could not generate animation'}), 404
    
    return jsonify({'file': anim_file})


@app.route('/api/trial-image/<int:participant>/<int:trial_n>')
def trial_image(participant, trial_n):
    """Get static image of trial's final state."""
    img_bytes = visualizer.generate_static_image(participant, trial_n)
    
    if img_bytes is None:
        return "Image not found", 404
    
    return send_file(img_bytes, mimetype='image/png')


@app.route('/api/analyze-patterns/<pattern_type>')
def analyze_patterns(pattern_type):
    """Analyze top 5 patterns for success or failure trials."""
    if pattern_type == 'success':
        subset_df = df[df['overall_correct'] == 1]
    else:
        subset_df = df[df['overall_correct'] == 0]
    
    position_counter = Counter()
    
    for _, row in subset_df.iterrows():
        final_positions = row['final_card_position_codes_1']
        if final_positions and len(final_positions) > 0:
            position_tuple = tuple(sorted(final_positions))
            position_counter[position_tuple] += 1
    
    top_patterns = position_counter.most_common(5)
    
    patterns_data = []
    for idx, (pattern, count) in enumerate(top_patterns):
        patterns_data.append({
            'id': idx,
            'pattern': list(pattern),
            'count': count,
            'cards': len(pattern)
        })
    
    return jsonify(patterns_data)


@app.route('/api/pattern-image/<pattern_type>/<int:pattern_id>')
def pattern_image(pattern_type, pattern_id):
    """Generate visualization image for a specific pattern."""
    if pattern_type == 'success':
        subset_df = df[df['overall_correct'] == 1]
    else:
        subset_df = df[df['overall_correct'] == 0]
    
    position_counter = Counter()
    for _, row in subset_df.iterrows():
        final_positions = row['final_card_position_codes_1']
        if final_positions and len(final_positions) > 0:
            position_tuple = tuple(sorted(final_positions))
            position_counter[position_tuple] += 1
    
    top_patterns = position_counter.most_common(5)
    
    if pattern_id >= len(top_patterns):
        return "Pattern not found", 404
    
    pattern, count = top_patterns[pattern_id]
    
    # Create isolated figure (thread-safe)
    fig = Figure(figsize=(7, 7), facecolor='white')
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    
    grid = np.empty((visualizer.grid_size, visualizer.grid_size), dtype=object)
    
    for card_str in pattern:
        card_info = visualizer.extract_card_info(card_str)
        if card_info:
            position_coords = visualizer.parse_position(card_info['position'])
            if position_coords:
                row, col = position_coords
                grid[row, col] = card_info
    
    trial_info = {
        'participant': f'Pattern #{pattern_id + 1}',
        'trialN': '',
        'condition': f'Frequency: {count} trials',
        'overall_correct': 1 if pattern_type == 'success' else 0
    }
    
    visualizer.plot_grid(grid, ax, len(pattern), len(pattern), trial_info)
    fig.tight_layout()
    
    # Save using canvas (thread-safe)
    img_bytes = io.BytesIO()
    canvas.print_png(img_bytes)
    img_bytes.seek(0)
    
    return send_file(img_bytes, mimetype='image/png')


@app.route('/api/pattern-trials/<pattern_type>/<int:pattern_id>')
def pattern_trials(pattern_type, pattern_id):
    """Get all trials that match a specific pattern."""
    if pattern_type == 'success':
        subset_df = df[df['overall_correct'] == 1]
    else:
        subset_df = df[df['overall_correct'] == 0]
    
    position_counter = Counter()
    for _, row in subset_df.iterrows():
        final_positions = row['final_card_position_codes_1']
        if final_positions and len(final_positions) > 0:
            position_tuple = tuple(sorted(final_positions))
            position_counter[position_tuple] += 1
    
    top_patterns = position_counter.most_common(5)
    
    if pattern_id >= len(top_patterns):
        return jsonify([])
    
    target_pattern, _ = top_patterns[pattern_id]
    target_sorted = tuple(sorted(target_pattern))
    
    matching_trials = []
    for _, row in subset_df.iterrows():
        final_positions = row['final_card_position_codes_1']
        if final_positions and len(final_positions) > 0:
            current_sorted = tuple(sorted(final_positions))
            if current_sorted == target_sorted:
                matching_trials.append({
                    'participant': int(row['participant']),
                    'trial': int(row['trialN']),
                    'condition': str(row['condition']),
                    'moves': len(row['movement_codes'])
                })
    
    return jsonify(matching_trials)


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Card Placement Analysis - Flask Application")
    print("=" * 60)
    print("\nLoading dataset...")
    
    if load_data():
        print(f"✓ Dataset loaded successfully")
        print(f"  - Total trials: {len(df)}")
        print(f"  - Participants: {df['participant'].nunique()}")
        print(f"  - Success rate: {(df['overall_correct'] == 1).mean() * 100:.1f}%")
        print("\n" + "=" * 60)
        print("Starting Flask development server...")
        print("=" * 60)
        print("\n🌐 Application running at: http://localhost:5001")
        print("\nPress Ctrl+C to stop the server\n")
        
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        print("\n✗ Error: Could not load dataset")
        print("\nPlease ensure:")
        print("  1. CardsDataset.csv is in the data/ folder")
        print("  2. The CSV file has the correct format")
        print("  3. File permissions allow reading")
        print("\n" + "=" * 60)
