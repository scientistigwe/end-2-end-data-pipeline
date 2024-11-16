from enum import Enum

class DatabaseType(Enum):
    """Database type enumeration"""
    POSTGRESQL = 'postgresql'
    MYSQL = 'mysql'
    MONGODB = 'mongodb'

    @classmethod
    def from_string(cls, value: str) -> 'DatabaseType':
        """Create instance from string representation

        Args:
            value: String representation of database type

        Returns:
            DatabaseType enum instance

        Raises:
            ValueError: If input string doesn't match any defined database type
        """
        # Return the value directly if it's already an instance of DatabaseType
        if isinstance(value, cls):
            return value

        # Create reverse mapping of values to enum members
        value_map = {member.value: member for member in cls}
        try:
            return value_map[value.lower()]
        except KeyError:
            valid_types = ", ".join(value_map.keys())
            raise ValueError(f"Invalid database type: {value}. Valid types are: {valid_types}")
