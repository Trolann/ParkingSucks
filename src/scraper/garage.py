from dataclasses import dataclass

@dataclass
class Garage:
    name: str
    address: str
    fullness: int
    timestamp: str

    def get_tuple(self):
        return self.name, self.address, self.fullness, self.timestamp
