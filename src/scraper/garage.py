from dataclasses import dataclass

@dataclass
class Garage:
    """
    This is a dataclass for a garage object. It contains attributes for the garage's name,
    address, fullness, and timestamp. The get_tuple method returns a tuple of these attributes.
    """
    name: str
    address: str
    fullness: int
    timestamp: str

    def __str__(self):
        return f"Garage: {self.name}, " \
               f"Address: {self.address}, " \
               f"Fullness: {self.fullness}, " \
               f"Timestamp: {self.timestamp}"

    def get_tuple(self):
        """
        This method returns a tuple of the garage's name, address, fullness, and timestamp.
        :return: (tuple) A tuple of the garage's name, address, fullness, and timestamp.
        """
        return self.name, self.address, self.fullness, self.timestamp