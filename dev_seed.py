"""
Development seed data for testing MShift.

This module provides sample data for development and testing.
Import and use load_dev_data() to populate the app with test data.
"""

from models import Person, Service


def load_dev_data(main_window):
    """
    Load development seed data into MainWindow.
    
    This adds:
    - 5 test people with varying percentages
    - Already configured services (Jour, Nuit, Planning Familial)
    
    Usage:
        if DEV_MODE:
            from dev_seed import load_dev_data
            load_dev_data(self)
    """
    # Add test people with different work percentages
    test_people = [
        Person("Tiphaine", "Angibaud", 100),
        Person("Marie", "Dubois", 80),
        Person("Sophie", "Martin", 100),
        Person("Claire", "Bernard", 50),
        Person("Julie", "Petit", 100),
        Person("Emma", "Rousseau", 80),
    ]
    
    for person in test_people:
        main_window._add_person_to_table(person)
    
    print(f"✅ Dev seed loaded: {len(test_people)} people added")


def load_dev_schedule_sample(main_window, year: int, month: int):
    """
    Load sample schedule assignments for testing rules engine.
    
    Creates some assignments to test:
    - Violation detection (missing/excess services)
    - Workload calculations
    - UI rendering
    
    Args:
        main_window: MainWindow instance
        year: Year for the schedule
        month: Month for the schedule (1-12)
    """
    if not main_window.people:
        print("⚠️ No people loaded. Load dev_data first.")
        return
    
    if not main_window.services:
        print("⚠️ No services loaded.")
        return
    
    # Get service IDs
    jour_service = next((s for s in main_window.services if s.name == "Jour"), None)
    nuit_service = next((s for s in main_window.services if s.name == "Nuit"), None)
    
    if not jour_service or not nuit_service:
        print("⚠️ Jour/Nuit services not found.")
        return
    
    # Create some sample assignments for first week
    # Day 1: 3 Jour, 3 Nuit (correct)
    # Day 2: 2 Jour, 4 Nuit (violations)
    # Day 3: 4 Jour, 2 Nuit (violations)
    
    people = main_window.people[:6]  # Use first 6 people
    
    # Day 1 - Correct
    main_window.apply_assignment_change(
        person_id=people[0].id, day=1, service_id=jour_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[1].id, day=1, service_id=jour_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[2].id, day=1, service_id=jour_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[3].id, day=1, service_id=nuit_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[4].id, day=1, service_id=nuit_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[5].id, day=1, service_id=nuit_service.id,
        year=year, month=month, reason="dev_seed"
    )
    
    # Day 2 - Missing Jour (only 2), Excess Nuit (4)
    main_window.apply_assignment_change(
        person_id=people[0].id, day=2, service_id=jour_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[1].id, day=2, service_id=jour_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[2].id, day=2, service_id=nuit_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[3].id, day=2, service_id=nuit_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[4].id, day=2, service_id=nuit_service.id,
        year=year, month=month, reason="dev_seed"
    )
    main_window.apply_assignment_change(
        person_id=people[5].id, day=2, service_id=nuit_service.id,
        year=year, month=month, reason="dev_seed"
    )
    
    # Refresh UI
    main_window.finalize_table_setup()
    
    print(f"✅ Dev schedule sample loaded for {year}-{month:02d}")
    print("   Day 1: Correct (3 Jour, 3 Nuit)")
    print("   Day 2: Violations (2 Jour, 4 Nuit)")
