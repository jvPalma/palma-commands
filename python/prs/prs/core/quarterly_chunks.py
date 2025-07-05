"""
Quarterly chunk system for efficient PR history building.
Divides time into manageable 3-month periods for API optimization.
"""

from datetime import datetime, date
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class QuarterChunk:
    """Represents a quarterly chunk with metadata."""
    chunk_number: int
    year: int
    quarter: int  # 1-4
    start_date: date
    end_date: date
    is_partial: bool = False
    
    def __str__(self):
        return f"Chunk {self.chunk_number}: Q{self.quarter} {self.year} ({self.start_date} to {self.end_date})"
    
    @property
    def date_range(self) -> str:
        """GitHub API compatible date range string."""
        return f"{self.start_date.isoformat()}..{self.end_date.isoformat()}"
    
    @property
    def description(self) -> str:
        """Human-readable description."""
        partial = " (partial)" if self.is_partial else ""
        return f"Q{self.quarter} {self.year}{partial}"


class QuarterlyChunkCalculator:
    """Calculate quarterly chunks for PR history fetching."""
    
    QUARTER_MONTHS = {
        1: (1, 3),   # Q1: Jan-Mar
        2: (4, 6),   # Q2: Apr-Jun
        3: (7, 9),   # Q3: Jul-Sep
        4: (10, 12)  # Q4: Oct-Dec
    }
    
    @staticmethod
    def get_quarter(date_obj: date) -> int:
        """Get quarter number (1-4) for a given date."""
        return (date_obj.month - 1) // 3 + 1
    
    @staticmethod
    def get_quarter_bounds(year: int, quarter: int) -> Tuple[date, date]:
        """Get start and end dates for a specific quarter."""
        start_month, end_month = QuarterlyChunkCalculator.QUARTER_MONTHS[quarter]
        
        # Start date is always the 1st of the quarter's first month
        start_date = date(year, start_month, 1)
        
        # End date is the last day of the quarter's last month
        if end_month == 12:
            end_date = date(year, 12, 31)
        elif end_month == 3:
            end_date = date(year, 3, 31)
        elif end_month == 6:
            end_date = date(year, 6, 30)
        else:  # September
            end_date = date(year, 9, 30)
            
        return start_date, end_date
    
    @classmethod
    def calculate_chunks(cls, 
                        reference_date: date = None, 
                        start_year: int = None,
                        end_year: int = None,
                        max_chunks: int = None) -> List[QuarterChunk]:
        """
        Calculate quarterly chunks working backwards from reference date.
        
        Args:
            reference_date: The date to calculate from (defaults to today)
            start_year: Earliest year to include (defaults to 3 years back)
            end_year: Latest year to include (defaults to current year)
            max_chunks: Maximum number of chunks (overrides year range)
            
        Returns:
            List of QuarterChunk objects, ordered from most recent to oldest
        """
        if reference_date is None:
            reference_date = date.today()
            
        if end_year is None:
            end_year = reference_date.year
            
        if start_year is None:
            start_year = reference_date.year - 2  # Default 3 years back
            
        chunks = []
        current_year = reference_date.year
        current_quarter = cls.get_quarter(reference_date)
        
        # Start with current quarter (partial)
        start_date, _ = cls.get_quarter_bounds(current_year, current_quarter)
        end_date = reference_date  # Today, not end of quarter
        
        chunks.append(QuarterChunk(
            chunk_number=1,
            year=current_year,
            quarter=current_quarter,
            start_date=start_date,
            end_date=end_date,
            is_partial=True
        ))
        
        # Work backwards through quarters
        year = current_year
        quarter = current_quarter - 1
        chunk_num = 2
        
        while True:
            # Check limits
            if max_chunks and len(chunks) >= max_chunks:
                break
            if year < start_year:
                break
            if year > end_year:
                year -= 1
                quarter = 4
                continue
                
            if quarter < 1:
                quarter = 4
                year -= 1
                continue
                
            start_date, end_date = cls.get_quarter_bounds(year, quarter)
            
            chunks.append(QuarterChunk(
                chunk_number=chunk_num,
                year=year,
                quarter=quarter,
                start_date=start_date,
                end_date=end_date,
                is_partial=False
            ))
            
            quarter -= 1
            chunk_num += 1
            
        return chunks
    
    @classmethod
    def validate_parameters(cls, start_year: int = None, end_year: int = None, max_chunks: int = None) -> List[str]:
        """Validate chunk parameters and return warnings."""
        warnings = []
        current_year = date.today().year
        
        if start_year and start_year > current_year:
            warnings.append(f"Start year {start_year} is in the future")
            
        if end_year and end_year > current_year:
            warnings.append(f"End year {end_year} is in the future")
            
        if start_year and end_year and start_year > end_year:
            warnings.append(f"Start year {start_year} is after end year {end_year}")
            
        if max_chunks and max_chunks > 40:
            warnings.append(f"Max chunks {max_chunks} may cause API rate limits (recommended: ≤40)")
            
        if start_year and start_year < current_year - 10:
            warnings.append(f"Start year {start_year} is very old - may result in many API calls")
            
        return warnings