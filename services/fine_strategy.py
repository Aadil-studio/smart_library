from abc import ABC, abstractmethod

class FineStrategy(ABC):
    @abstractmethod
    def calculate_fine(self, days_overdue: int) -> float:
        pass

class StudentFineStrategy(FineStrategy):
    """Rs. 10 per day by default; the rate is configurable in System Settings."""
    def __init__(self, rate_per_day: float = 10.0):
        self.rate_per_day = float(rate_per_day)

    def calculate_fine(self, days_overdue: int) -> float:
        return max(0.0, days_overdue * self.rate_per_day)

class FacultyFineStrategy(FineStrategy):
    def __init__(self, rate_per_day: float = 2.0):
        self.rate_per_day = float(rate_per_day)

    def calculate_fine(self, days_overdue: int) -> float:
        return max(0.0, days_overdue * self.rate_per_day)

class FineContext:
    def __init__(self, strategy: FineStrategy | None = None):
        self._strategy = strategy or StudentFineStrategy()

    def set_strategy(self, strategy: FineStrategy):
        self._strategy = strategy

    def compute_fine(self, days_overdue: int) -> float:
        return self._strategy.calculate_fine(days_overdue)
