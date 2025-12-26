import sys
import os
sys.path.append(os.path.join(os.getcwd(), "src"))
from edusched.domain.resource import Resource

def test_can_satisfy_structured_field():
    # Create a resource with a structured field 'building_id'
    r = Resource(id="r1", resource_type="room", building_id="ScienceHall")
    
    # Requirement: We need a room in ScienceHall
    requirements = {"building_id": "ScienceHall"}
    
    # Check if it satisfies the requirement
    result = r.can_satisfy(requirements)
    
    print(f"Resource building_id: {r.building_id}")
    print(f"Requirement: {requirements}")
    print(f"can_satisfy result: {result}")
    
    if result is False:
        print("BUG CONFIRMED: can_satisfy failed to check the structured 'building_id' field.")
    else:
        print("False alarm: It worked.")

if __name__ == "__main__":
    test_can_satisfy_structured_field()
