from abc import ABC, abstractmethod

class FineStrategy(ABC):
    @abstractmethod
    def calculate_fine(self, days_overdue: int) -> float:
        pass

class StudentFineStrategy(FineStrategy):
    def calculate_fine(self, days_overdue: int) -> float:
        return max(0.0, days_overdue * 10.0)

class FacultyFineStrategy(FineStrategy):
    def calculate_fine(self, days_overdue: int) -> float:
        return max(0.0, days_overdue * 2.0)

class FineContext:
    def __init__(self, strategy: FineStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: FineStrategy):
        self._strategy = strategy

    def compute_fine(self, days_overdue: int) -> float:
        return self._strategy.calculate_fine(days_overdue)