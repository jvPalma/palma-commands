"""
Spinner Manager for enhanced watch mode countdown timer.

Manages countdown display using Rich Progress/Spinner components
with smooth updates for the enhanced watch mode experience.
"""

import time
from typing import Optional
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.console import Console


class SpinnerManager:
    """
    Manages countdown timer display with Rich spinners and progress bars.
    
    Provides countdown visualization for watch mode refresh intervals
    with spinner animation and remaining time display.
    """
    
    # Spinner styles to cycle through
    SPINNER_STYLES = [
        "dots", "dots2", "dots3", "dots4", "dots5", "dots6", "dots7", "dots8", "dots9", "dots10",
        "line", "line2", "bouncingBar", "bouncingBall", "smiley", "monkey", "hearts", "clock",
        "earth", "moon", "runner", "pong", "shark", "dqpb", "weather", "christmas"
    ]
    
    def __init__(self, interval: int):
        """
        Initialize the spinner manager.
        
        Args:
            interval: The update interval in seconds
        """
        self.interval = interval
        self._current_spinner_index = 0
        self._start_time: Optional[float] = None
        self._progress: Optional[Progress] = None
        self._task_id: Optional[int] = None
    
    def get_countdown_display(self, remaining_seconds: int) -> Text:
        """
        Get a Rich Text object displaying the countdown timer.
        
        Args:
            remaining_seconds: Number of seconds remaining until next update
            
        Returns:
            Rich Text object with animated countdown display
        """
        # Create spinner character
        spinner_char = self._get_current_spinner_char()
        
        # Create the countdown text
        countdown_text = Text()
        
        # Add spinner with animation
        countdown_text.append(f"{spinner_char} ", style="cyan")
        
        # Add countdown
        if remaining_seconds > 0:
            minutes, seconds = divmod(remaining_seconds, 60)
            if minutes > 0:
                countdown_text.append(f"Next update in: {minutes}m {seconds}s", style="yellow")
            else:
                countdown_text.append(f"Next update in: {seconds}s", style="yellow")
        else:
            countdown_text.append("Updating...", style="green")
        
        return countdown_text
    
    def get_enhanced_countdown_display(self, remaining_seconds: int, modes: dict, show_shortcuts: bool = True) -> Text:
        """
        Get enhanced countdown display with keyboard shortcuts and current modes.
        
        Args:
            remaining_seconds: Number of seconds remaining until next update
            modes: Current display modes dictionary
            show_shortcuts: Whether to show keyboard shortcuts
            
        Returns:
            Rich Text object with enhanced countdown display
        """
        display_text = Text()
        
        # Add keyboard shortcuts if requested
        if show_shortcuts:
            display_text.append("Press ", style="dim")
            display_text.append("c", style="bold cyan")
            display_text.append("/", style="dim")
            display_text.append("r", style="bold cyan")
            display_text.append("/", style="dim")
            display_text.append("l", style="bold cyan")
            display_text.append(" to cycle modes", style="dim")
            display_text.append(" | ", style="dim")
        
        # Add current modes
        mode_parts = []
        for feature in ["checks", "reviews", "labels"]:
            if feature in modes:
                mode_parts.append(f"{feature.capitalize()}: {modes[feature]}")
        
        if mode_parts:
            display_text.append(" | ".join(mode_parts), style="white")
            display_text.append(" | ", style="dim")
        
        # Add countdown with spinner
        spinner_char = self._get_current_spinner_char()
        display_text.append(f"{spinner_char} ", style="cyan")
        
        if remaining_seconds > 0:
            minutes, seconds = divmod(remaining_seconds, 60)
            if minutes > 0:
                display_text.append(f"Next update in: {minutes}m {seconds}s", style="yellow")
            else:
                display_text.append(f"Next update in: {seconds}s", style="yellow")
        else:
            display_text.append("Updating...", style="green")
        
        return display_text
    
    def reset_countdown(self) -> None:
        """Reset the countdown timer to start fresh."""
        self._start_time = time.time()
        # Advance to next spinner style for visual variety
        self._current_spinner_index = (self._current_spinner_index + 1) % len(self.SPINNER_STYLES)
    
    def _get_current_spinner_char(self) -> str:
        """
        Get the current spinner character based on time and style.
        
        Returns:
            Single character string representing current spinner frame
        """
        # Define spinner characters for different styles
        spinner_frames = {
            "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
            "dots2": ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],
            "dots3": ["⠋", "⠙", "⠚", "⠞", "⠖", "⠦", "⠴", "⠲", "⠳", "⠓"],
            "line": ["-", "\\", "|", "/"],
            "bouncingBar": ["[    ]", "[=   ]", "[==  ]", "[=== ]", "[ ===]", "[  ==]", "[   =]", "[    ]", "[   =]", "[  ==]", "[ ===]", "[====]", "[=== ]", "[==  ]", "[=   ]"],
            "clock": ["🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛"],
            "earth": ["🌍", "🌎", "🌏"],
            "moon": ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"],
            "hearts": ["💛", "💙", "💜", "🧡", "❤️"],
            "weather": ["☀️", "⛅", "🌤️", "🌦️", "🌧️", "⛈️", "🌩️", "🌨️"]
        }
        
        # Get current style
        current_style = self.SPINNER_STYLES[self._current_spinner_index]
        
        # Use dots as fallback if style not found
        frames = spinner_frames.get(current_style, spinner_frames["dots"])
        
        # Calculate frame based on time (animate every 0.1 seconds)
        frame_index = int(time.time() * 10) % len(frames)
        return frames[frame_index]
    
    def get_progress_bar(self, remaining_seconds: int) -> Optional[str]:
        """
        Get a simple text-based progress bar for the countdown.
        
        Args:
            remaining_seconds: Number of seconds remaining
            
        Returns:
            String representation of progress bar or None if not applicable
        """
        if remaining_seconds <= 0 or self.interval <= 0:
            return None
        
        # Calculate progress (0.0 to 1.0)
        elapsed = self.interval - remaining_seconds
        progress = min(1.0, max(0.0, elapsed / self.interval))
        
        # Create text progress bar
        bar_width = 20
        filled_width = int(progress * bar_width)
        empty_width = bar_width - filled_width
        
        bar = "█" * filled_width + "░" * empty_width
        percentage = int(progress * 100)
        
        return f"[{bar}] {percentage}%"
    
    def create_rich_progress(self, console: Console) -> Progress:
        """
        Create a Rich Progress object for more advanced countdown display.
        
        Args:
            console: Rich console instance
            
        Returns:
            Configured Rich Progress object
        """
        if self._progress is None:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}", justify="left"),
                BarColumn(bar_width=20),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console,
                refresh_per_second=10,
                expand=True
            )
        
        return self._progress
    
    def update_progress_task(self, remaining_seconds: int, description: str = "Next update") -> None:
        """
        Update the progress task with current countdown state.
        
        Args:
            remaining_seconds: Number of seconds remaining
            description: Description text for the progress task
        """
        if self._progress is None or self._task_id is None:
            return
        
        # Calculate progress
        elapsed = self.interval - remaining_seconds
        progress_value = min(100.0, max(0.0, (elapsed / self.interval) * 100))
        
        # Update the task
        self._progress.update(
            self._task_id, 
            completed=progress_value,
            description=description
        )
    
    def start_progress_task(self, description: str = "Next update") -> int:
        """
        Start a new progress task.
        
        Args:
            description: Description for the progress task
            
        Returns:
            Task ID for the created task
        """
        if self._progress is None:
            raise RuntimeError("Progress not initialized. Call create_rich_progress() first.")
        
        self._task_id = self._progress.add_task(description, total=100.0)
        return self._task_id
    
    def stop_progress(self) -> None:
        """Stop and clean up the progress display."""
        if self._progress is not None:
            try:
                self._progress.stop()
            except Exception:
                pass  # Ignore errors during cleanup
            self._progress = None
            self._task_id = None
    
    def get_current_spinner_style(self) -> str:
        """Get the name of the current spinner style."""
        return self.SPINNER_STYLES[self._current_spinner_index]
    
    def set_spinner_style(self, style_name: str) -> bool:
        """
        Set the spinner style by name.
        
        Args:
            style_name: Name of the spinner style to use
            
        Returns:
            True if style was set successfully, False if style not found
        """
        if style_name in self.SPINNER_STYLES:
            self._current_spinner_index = self.SPINNER_STYLES.index(style_name)
            return True
        return False
    
    def __str__(self) -> str:
        """String representation of the SpinnerManager."""
        return f"SpinnerManager(interval={self.interval}s, style={self.get_current_spinner_style()})"