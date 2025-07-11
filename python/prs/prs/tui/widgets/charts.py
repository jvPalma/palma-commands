"""
Chart widgets for the TUI analytics dashboard.

Provides ASCII-based charts and visualizations for metrics display
within the terminal user interface.
"""

from typing import List, Tuple, Optional, Union
import math

from textual.app import ComposeResult
from textual.widgets import Static
from textual.reactive import reactive


class SparklineChart(Static):
    """
    ASCII sparkline chart widget.
    
    Displays a simple line chart using Unicode block characters
    for trending data visualization.
    """
    
    data = reactive([], recompose=True)
    height = reactive(3)
    show_values = reactive(False)
    
    # Unicode block characters for sparklines
    BLOCKS = [' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    
    def __init__(self, data: List[Union[int, float]] = None, 
                 height: int = 3, show_values: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        self.height = height
        self.show_values = show_values
        
    def render(self) -> str:
        """Render the sparkline chart."""
        if not self.data or len(self.data) < 2:
            return "No data available"
            
        # Normalize data to chart height
        min_val = min(self.data)
        max_val = max(self.data)
        
        if max_val == min_val:
            # All values are the same
            normalized = [len(self.BLOCKS) // 2] * len(self.data)
        else:
            range_val = max_val - min_val
            normalized = [
                int((val - min_val) / range_val * (len(self.BLOCKS) - 1))
                for val in self.data
            ]
        
        # Create sparkline
        sparkline = ''.join(self.BLOCKS[val] for val in normalized)
        
        # Add value labels if requested
        if self.show_values:
            value_line = ' '.join(f"{val:3.0f}" for val in self.data[-10:])  # Last 10 values
            return f"{sparkline}\n{value_line}"
        
        return sparkline


class BarChart(Static):
    """
    ASCII bar chart widget.
    
    Displays vertical bar chart using Unicode block characters
    with optional labels and values.
    """
    
    data = reactive([], recompose=True)
    labels = reactive([])
    height = reactive(8)
    show_values = reactive(True)
    
    # Unicode block characters for bars
    BARS = [' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    
    def __init__(self, data: List[Union[int, float]] = None,
                 labels: List[str] = None, height: int = 8, 
                 show_values: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        self.labels = labels or []
        self.height = height
        self.show_values = show_values
        
    def render(self) -> str:
        """Render the bar chart."""
        if not self.data:
            return "No data available"
            
        # Normalize data to chart height
        max_val = max(self.data) if self.data else 1
        if max_val == 0:
            max_val = 1
            
        normalized = [val / max_val for val in self.data]
        
        # Create chart lines
        lines = []
        
        # Draw bars from top to bottom
        for row in range(self.height, 0, -1):
            line = ""
            for i, norm_val in enumerate(normalized):
                bar_height = norm_val * self.height
                
                if bar_height >= row:
                    # Full block
                    line += "█"
                elif bar_height >= row - 1:
                    # Partial block
                    partial_height = (bar_height - (row - 1)) * len(self.BARS)
                    block_index = min(int(partial_height), len(self.BARS) - 1)
                    line += self.BARS[block_index]
                else:
                    # Empty space
                    line += " "
                    
                # Add spacing between bars
                if i < len(normalized) - 1:
                    line += " "
                    
            lines.append(line)
            
        # Add labels if provided
        if self.labels:
            label_line = ""
            for i, label in enumerate(self.labels):
                # Truncate labels to fit
                label = label[:3] if len(label) > 3 else label
                label_line += f"{label:^3}"
                if i < len(self.labels) - 1:
                    label_line += " "
            lines.append("-" * len(label_line))
            lines.append(label_line)
            
        # Add values if requested
        if self.show_values:
            value_line = ""
            for i, val in enumerate(self.data):
                value_line += f"{val:3.0f}"
                if i < len(self.data) - 1:
                    value_line += " "
            lines.append(value_line)
            
        return "\n".join(lines)


class PieChart(Static):
    """
    ASCII pie chart widget.
    
    Displays a simple pie chart representation using text
    with percentages and labels.
    """
    
    data = reactive([], recompose=True)
    
    def __init__(self, data: List[Tuple[str, Union[int, float]]] = None, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        
    def render(self) -> str:
        """Render the pie chart."""
        if not self.data:
            return "No data available"
            
        # Calculate total and percentages
        total = sum(val for _, val in self.data)
        if total == 0:
            return "No data to display"
            
        lines = []
        
        # Create simple text-based pie representation
        for label, value in self.data:
            percentage = (value / total) * 100
            
            # Create a simple bar representation
            bar_length = int(percentage / 5)  # Scale down for display
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            lines.append(f"{label:12} {bar} {percentage:5.1f}% ({value})")
            
        return "\n".join(lines)


class ProgressChart(Static):
    """
    Progress visualization chart.
    
    Shows progress towards goals or targets with visual indicators.
    """
    
    current = reactive(0)
    target = reactive(100)
    label = reactive("")
    
    def __init__(self, current: Union[int, float] = 0,
                 target: Union[int, float] = 100,
                 label: str = "", **kwargs):
        super().__init__(**kwargs)
        self.current = current
        self.target = target
        self.label = label
        
    def render(self) -> str:
        """Render the progress chart."""
        if self.target <= 0:
            return "Invalid target value"
            
        # Calculate progress percentage
        progress = min(self.current / self.target, 1.0)
        percentage = progress * 100
        
        # Create progress bar
        bar_width = 30
        filled_width = int(progress * bar_width)
        
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Format display
        if self.label:
            return f"{self.label}\n{bar} {percentage:5.1f}% ({self.current}/{self.target})"
        else:
            return f"{bar} {percentage:5.1f}% ({self.current}/{self.target})"


class TrendChart(Static):
    """
    Trend visualization with direction indicators.
    
    Shows trend direction and magnitude using arrows and colors.
    """
    
    data = reactive([])
    periods = reactive(["Previous", "Current"])
    
    def __init__(self, data: List[Union[int, float]] = None,
                 periods: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        self.periods = periods or ["Previous", "Current"]
        
    def render(self) -> str:
        """Render the trend chart."""
        if len(self.data) < 2:
            return "Insufficient data for trend"
            
        lines = []
        
        for i in range(1, len(self.data)):
            previous = self.data[i-1]
            current = self.data[i]
            
            # Calculate change
            if previous == 0:
                change_pct = 0 if current == 0 else 100
            else:
                change_pct = ((current - previous) / previous) * 100
                
            # Determine trend direction
            if change_pct > 5:
                arrow = "↗️"
                trend = "UP"
            elif change_pct < -5:
                arrow = "↘️"
                trend = "DOWN"
            else:
                arrow = "→"
                trend = "FLAT"
                
            # Format period labels
            prev_label = self.periods[i-1] if i-1 < len(self.periods) else f"Period {i-1}"
            curr_label = self.periods[i] if i < len(self.periods) else f"Period {i}"
            
            lines.append(f"{prev_label} → {curr_label}: {current:6.1f} {arrow} {trend} ({change_pct:+5.1f}%)")
            
        return "\n".join(lines)


class HistogramChart(Static):
    """
    ASCII histogram chart widget.
    
    Displays data distribution using horizontal bars.
    """
    
    data = reactive([])
    bins = reactive(10)
    
    def __init__(self, data: List[Union[int, float]] = None,
                 bins: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        self.bins = bins
        
    def render(self) -> str:
        """Render the histogram."""
        if not self.data:
            return "No data available"
            
        # Calculate histogram bins
        min_val = min(self.data)
        max_val = max(self.data)
        
        if min_val == max_val:
            return f"All values are {min_val}"
            
        bin_width = (max_val - min_val) / self.bins
        bin_counts = [0] * self.bins
        
        # Count values in each bin
        for value in self.data:
            bin_index = min(int((value - min_val) / bin_width), self.bins - 1)
            bin_counts[bin_index] += 1
            
        # Find maximum count for scaling
        max_count = max(bin_counts)
        
        lines = []
        for i, count in enumerate(bin_counts):
            # Calculate bin range
            bin_start = min_val + i * bin_width
            bin_end = min_val + (i + 1) * bin_width
            
            # Create bar
            bar_length = int((count / max_count) * 20) if max_count > 0 else 0
            bar = "█" * bar_length
            
            lines.append(f"{bin_start:6.1f}-{bin_end:6.1f} |{bar:<20} {count}")
            
        return "\n".join(lines)


class MultiLineChart(Static):
    """
    Multi-line ASCII chart widget.
    
    Displays multiple data series on the same chart with different markers.
    """
    
    series = reactive([])
    labels = reactive([])
    height = reactive(10)
    
    MARKERS = ['█', '▓', '▒', '░', '▪', '▫', '●', '○']
    
    def __init__(self, series: List[List[Union[int, float]]] = None,
                 labels: List[str] = None, height: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.series = series or []
        self.labels = labels or []
        self.height = height
        
    def render(self) -> str:
        """Render the multi-line chart."""
        if not self.series:
            return "No data available"
            
        # Find global min/max for normalization
        all_values = [val for series_data in self.series for val in series_data]
        if not all_values:
            return "No data points"
            
        min_val = min(all_values)
        max_val = max(all_values)
        
        if min_val == max_val:
            return f"All values are {min_val}"
            
        # Normalize all series
        normalized_series = []
        for series_data in self.series:
            normalized = [
                (val - min_val) / (max_val - min_val) * (self.height - 1)
                for val in series_data
            ]
            normalized_series.append(normalized)
            
        # Determine chart width
        max_length = max(len(series_data) for series_data in self.series)
        
        # Create chart grid
        lines = []
        for row in range(self.height, 0, -1):
            line = ""
            for col in range(max_length):
                char = " "
                
                # Check each series for a point at this position
                for series_idx, series_data in enumerate(normalized_series):
                    if col < len(series_data):
                        point_height = series_data[col]
                        if abs(point_height - (row - 1)) < 0.5:
                            marker_idx = series_idx % len(self.MARKERS)
                            char = self.MARKERS[marker_idx]
                            break
                            
                line += char
                
            lines.append(line)
            
        # Add legend if labels provided
        if self.labels:
            lines.append("")
            lines.append("Legend:")
            for i, label in enumerate(self.labels):
                if i < len(self.MARKERS):
                    marker = self.MARKERS[i]
                    lines.append(f"{marker} {label}")
                    
        return "\n".join(lines)