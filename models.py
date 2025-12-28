import uuid
from typing import Optional, Dict

class Service:
    def __init__(self, name, short_name, hours, color_hex):
        self.id = str(uuid.uuid4()) # Unique identifier
        self.name = name
        self.short_name = short_name
        self.hours = hours
        self.color_hex = color_hex

class Person:
    def __init__(self, FullName, ShortName, percentage):
        self.id = str(uuid.uuid4()) # Unique identifier
        self.name = FullName
        self.short_name = ShortName
        self.percentage = percentage

class MonthData:
    def __init__(self, year : int, month : int):
        self.year = year
        self.month = month
        # key : (person.id, day)
        self.assignments = {}

    def get_service(self, person_id, day):
        return self.assignments.get((person_id, day))

    def set_service(self, person_id, day, service_id):
        if service_id is None :
            self.assignments.pop((person_id, day), None)
        
        else :
            self.assignments[(person_id, day)] = service_id

