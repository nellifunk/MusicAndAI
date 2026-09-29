from abc import ABC, abstractmethod


class ControllerAdapter(ABC):
    @abstractmethod
    def select_cell(self, row: int, col: int):
        raise NotImplementedError

    @abstractmethod
    def set_valence(self, value: float):
        raise NotImplementedError

    @abstractmethod
    def set_energy(self, value: float):
        raise NotImplementedError

    @abstractmethod
    def set_complexity(self, value: float):
        raise NotImplementedError

    @abstractmethod
    def set_brightness(self, value: float):
        raise NotImplementedError

    @abstractmethod
    def save_interpretation(self, name: str):
        raise NotImplementedError

