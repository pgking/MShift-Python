"""
Comprehensive test suite for MShift application.

Run with: python tests.py
Or with verbose output: python tests.py -v

Tests cover:
- Model creation, serialization, edge cases
- Section management
- Schema pattern application & assignment logic
- Controller operations (assignments, stats, sections, recent files)
- Rules engine & violation detection
- Preferences serialization
- Undo/Redo manager
- File I/O round-trip operations
"""

import unittest
import os
import tempfile
import json
import calendar
from datetime import datetime

from models import Person, Service, MonthData, Schema, SchemaAssignment, Section
from controller import ScheduleController
from rules import StaffingRule, ServiceKind, Severity, evaluate_rules, DEFAULT_RULES
from preferences import Preferences
from undo_manager import UndoManager, UndoableAction, ScheduleUndoManager


# ================================================================
# PERSON MODEL
# ================================================================
class TestPersonModel(unittest.TestCase):
    def test_creation(self):
        p = Person(prenom="Marie", nom="Dupont", percentage=100)
        self.assertEqual(p.prenom, "Marie")
        self.assertEqual(p.nom, "Dupont")
        self.assertEqual(p.percentage, 100)
        self.assertIsNotNone(p.id)

    def test_display_name(self):
        p = Person(prenom="marie", nom="dupont", percentage=100)
        self.assertEqual(p.display_name, "Marie DUPONT")

    def test_display_name_no_prenom(self):
        p = Person(prenom="", nom="dupont", percentage=100)
        self.assertEqual(p.display_name, "DUPONT")

    def test_short_name_default(self):
        p = Person(prenom="Marie", nom="Dupont", percentage=100)
        self.assertEqual(p.short_name, "M. Dupont")

    def test_short_name_no_prenom(self):
        p = Person(prenom="", nom="Dupont", percentage=100)
        self.assertEqual(p.short_name, "Dupont")

    def test_short_name_custom(self):
        p = Person(prenom="Marie", nom="Dupont", percentage=100, short_name="MD")
        self.assertEqual(p.short_name, "MD")

    def test_serialization_roundtrip(self):
        p = Person(prenom="Marie", nom="Dupont", percentage=80, section_id="sec1")
        data = p.to_dict()
        p2 = Person(**data)
        self.assertEqual(p2.prenom, "Marie")
        self.assertEqual(p2.nom, "Dupont")
        self.assertEqual(p2.percentage, 80)
        self.assertEqual(p2.id, p.id)
        self.assertEqual(p2.section_id, "sec1")

    def test_whitespace_stripped(self):
        p = Person(prenom="  Marie  ", nom="  Dupont  ", percentage=100)
        self.assertEqual(p.prenom, "Marie")
        self.assertEqual(p.nom, "Dupont")


# ================================================================
# SERVICE MODEL
# ================================================================
class TestServiceModel(unittest.TestCase):
    def test_creation(self):
        s = Service("Jour", "J", 12, "#A3D5FF")
        self.assertEqual(s.name, "Jour")
        self.assertEqual(s.short_name, "J")
        self.assertEqual(s.hours, 12)
        self.assertTrue(s.is_visible)

    def test_duration_normal(self):
        s = Service("Jour", "J", 12, "#A3D5FF")
        self.assertEqual(s.get_duration(2026, 1, 15, set()), 12.0)

    def test_duration_ca_weekday(self):
        s = Service("Congés Annuels", "CA", 7, "#FFD6A3")
        # 2026-01-15 is Thursday
        self.assertEqual(s.get_duration(2026, 1, 15, set()), 7.0)

    def test_duration_ca_percentage(self):
        s = Service("Congés Annuels", "CA", 7, "#FFD6A3")
        # 80% of 7h = 5.6h
        self.assertAlmostEqual(s.get_duration(2026, 1, 15, set(), 80), 5.6)


    def test_duration_ca_weekend(self):
        s = Service("Congés Annuels", "CA", 7, "#FFD6A3")
        # 2026-01-18 is Sunday
        self.assertEqual(s.get_duration(2026, 1, 18, set()), 0.0)

    def test_duration_ca_holiday(self):
        s = Service("Congés Annuels", "CA", 7, "#FFD6A3")
        self.assertEqual(s.get_duration(2026, 1, 15, {15}), 0.0)

    def test_invisible_service(self):
        s = Service("Hidden", "H", 0, "#000", is_visible=False)
        self.assertFalse(s.is_visible)

    def test_serialization_roundtrip(self):
        s = Service("Jour", "J", 12, "#A3D5FF", is_visible=False)
        data = s.to_dict()
        s2 = Service(**data)
        self.assertEqual(s2.name, "Jour")
        self.assertEqual(s2.id, s.id)
        self.assertFalse(s2.is_visible)


# ================================================================
# SECTION MODEL
# ================================================================
class TestSectionModel(unittest.TestCase):
    def test_creation(self):
        sec = Section(id="s1", label="Test Section")
        self.assertEqual(sec.id, "s1")
        self.assertEqual(sec.label, "Test Section")
        self.assertEqual(sec.people_ids, [])

    def test_add_person(self):
        sec = Section(id="s1", label="Test")
        sec.add_person("p1")
        sec.add_person("p2")
        self.assertEqual(sec.people_ids, ["p1", "p2"])

    def test_add_person_at_index(self):
        sec = Section(id="s1", label="Test", people_ids=["p1", "p3"])
        sec.add_person("p2", index=1)
        self.assertEqual(sec.people_ids, ["p1", "p2", "p3"])

    def test_add_person_deduplicates(self):
        sec = Section(id="s1", label="Test", people_ids=["p1", "p2", "p3"])
        sec.add_person("p1", index=2)
        self.assertEqual(len(sec.people_ids), 3)
        self.assertEqual(sec.people_ids[2], "p1")

    def test_remove_person(self):
        sec = Section(id="s1", label="Test", people_ids=["p1", "p2"])
        self.assertTrue(sec.remove_person("p1"))
        self.assertEqual(sec.people_ids, ["p2"])
        self.assertFalse(sec.remove_person("p99"))

    def test_reorder_person(self):
        sec = Section(id="s1", label="Test", people_ids=["p1", "p2", "p3"])
        sec.reorder_person("p3", 0)
        self.assertEqual(sec.people_ids, ["p3", "p1", "p2"])

    def test_sort_alphabetically(self):
        people = {
            "p1": Person(prenom="Charlie", nom="Zebra", percentage=100, id="p1"),
            "p2": Person(prenom="Alice", nom="Apple", percentage=100, id="p2"),
            "p3": Person(prenom="Bob", nom="Mango", percentage=100, id="p3"),
        }
        sec = Section(id="s1", label="Test", people_ids=["p1", "p2", "p3"])
        sec.sort_people_alphabetically(people)
        self.assertEqual(sec.people_ids, ["p2", "p3", "p1"])

    def test_serialization_roundtrip(self):
        sec = Section(id="s1", label="Test", people_ids=["p1", "p2"], is_collapsed=True)
        data = sec.to_dict()
        sec2 = Section.from_dict(data)
        self.assertEqual(sec2.id, "s1")
        self.assertEqual(sec2.people_ids, ["p1", "p2"])
        self.assertTrue(sec2.is_collapsed)


# ================================================================
# SCHEMA MODEL
# ================================================================
class TestSchemaModel(unittest.TestCase):
    def test_creation(self):
        schema = Schema(name="Week", start_weekday=0, span_days=7)
        self.assertEqual(schema.name, "Week")
        self.assertEqual(schema.span_days, 7)
        self.assertEqual(len(schema.pattern), 0)

    def test_set_and_get_service(self):
        schema = Schema("Week", 0, 7)
        schema.set_service(0, "s1")
        schema.set_service(1, "s2")
        self.assertEqual(schema.get_service(0), "s1")
        self.assertEqual(schema.get_service(1), "s2")
        self.assertIsNone(schema.get_service(5))

    def test_clear_service(self):
        schema = Schema("Week", 0, 7)
        schema.set_service(0, "s1")
        schema.set_service(0, None)
        self.assertIsNone(schema.get_service(0))

    def test_serialization_roundtrip(self):
        schema = Schema("Week", 0, 7)
        schema.set_service(0, "s1")
        schema.set_service(3, "s2")
        data = schema.to_dict()
        # JSON round-trip (keys become strings)
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        restored = Schema.from_dict(restored_data)
        self.assertEqual(restored.name, "Week")
        self.assertEqual(restored.get_service(0), "s1")
        self.assertEqual(restored.get_service(3), "s2")
        self.assertIsNone(restored.get_service(1))


# ================================================================
# SCHEMA ASSIGNMENT MODEL
# ================================================================
class TestSchemaAssignment(unittest.TestCase):
    def test_always_mode(self):
        sa = SchemaAssignment("p1", "s1", repeat_mode="always", start_year=2026, start_month=1)
        self.assertTrue(sa.should_apply_to_month(2026, 1))
        self.assertTrue(sa.should_apply_to_month(2026, 6))
        self.assertTrue(sa.should_apply_to_month(2027, 1))
        self.assertFalse(sa.should_apply_to_month(2025, 12))

    def test_limited_mode(self):
        sa = SchemaAssignment("p1", "s1", repeat_mode="limited", repeat_months=3,
                              start_year=2026, start_month=1)
        self.assertTrue(sa.should_apply_to_month(2026, 1))
        self.assertTrue(sa.should_apply_to_month(2026, 2))
        self.assertTrue(sa.should_apply_to_month(2026, 3))
        self.assertFalse(sa.should_apply_to_month(2026, 4))
        self.assertFalse(sa.should_apply_to_month(2025, 12))

    def test_limited_cross_year(self):
        sa = SchemaAssignment("p1", "s1", repeat_mode="limited", repeat_months=3,
                              start_year=2026, start_month=11)
        self.assertTrue(sa.should_apply_to_month(2026, 11))
        self.assertTrue(sa.should_apply_to_month(2026, 12))
        self.assertTrue(sa.should_apply_to_month(2027, 1))
        self.assertFalse(sa.should_apply_to_month(2027, 2))

    def test_always_no_start_date(self):
        sa = SchemaAssignment("p1", "s1", repeat_mode="always")
        self.assertTrue(sa.should_apply_to_month(2020, 1))

    def test_limited_no_start_date(self):
        sa = SchemaAssignment("p1", "s1", repeat_mode="limited", repeat_months=3)
        self.assertFalse(sa.should_apply_to_month(2026, 1))

    def test_overwrite_flag(self):
        sa = SchemaAssignment("p1", "s1", overwrite_existing=False)
        self.assertFalse(sa.overwrite_existing)

    def test_serialization_roundtrip(self):
        sa = SchemaAssignment("p1", "s1", repeat_mode="limited", repeat_months=3,
                              start_year=2026, start_month=1, overwrite_existing=True)
        data = sa.to_dict()
        restored = SchemaAssignment.from_dict(data)
        self.assertEqual(restored.person_id, "p1")
        self.assertEqual(restored.repeat_mode, "limited")
        self.assertEqual(restored.repeat_months, 3)
        self.assertTrue(restored.overwrite_existing)


# ================================================================
# MONTH DATA MODEL
# ================================================================
class TestMonthData(unittest.TestCase):
    def test_creation(self):
        md = MonthData(2026, 1)
        self.assertEqual(md.year, 2026)
        self.assertEqual(md.month, 1)

    def test_set_get_service(self):
        md = MonthData(2026, 1)
        md.set_service("p1", 15, "s1")
        self.assertEqual(md.get_service("p1", 15), "s1")
        self.assertIsNone(md.get_service("p1", 16))
        self.assertIsNone(md.get_service("p2", 15))

    def test_clear_service(self):
        md = MonthData(2026, 1)
        md.set_service("p1", 15, "s1")
        md.set_service("p1", 15, None)
        self.assertIsNone(md.get_service("p1", 15))

    def test_comments(self):
        md = MonthData(2026, 1)
        md.set_comment("p1", "Hello")
        self.assertEqual(md.get_comment("p1"), "Hello")
        self.assertEqual(md.get_comment("p2"), "")
        md.set_comment("p1", "")
        self.assertEqual(md.get_comment("p1"), "")

    def test_notes(self):
        md = MonthData(2026, 1)
        md.set_note("p1", 5, "Note text")
        self.assertEqual(md.get_note("p1", 5), "Note text")
        self.assertIsNone(md.get_note("p1", 6))
        md.set_note("p1", 5, "")
        self.assertIsNone(md.get_note("p1", 5))

    def test_clearing_service_clears_note(self):
        md = MonthData(2026, 1)
        md.set_service("p1", 5, "s1")
        md.set_note("p1", 5, "Some note")
        md.set_service("p1", 5, None)
        self.assertIsNone(md.get_note("p1", 5))

    def test_holidays(self):
        md = MonthData(2026, 1)
        md.toggle_holiday(15)
        self.assertIn(15, md.holidays)
        md.toggle_holiday(15)
        self.assertNotIn(15, md.holidays)

    def test_multiple_holidays(self):
        md = MonthData(2026, 1)
        md.toggle_holiday(1)
        md.toggle_holiday(25)
        self.assertEqual(md.holidays, {1, 25})

    def test_serialization_roundtrip(self):
        md = MonthData(2026, 3)
        md.set_service("p1", 15, "s1")
        md.set_service("p2", 16, "s2")
        md.set_comment("p1", "Comment")
        md.set_note("p1", 15, "My note")
        md.toggle_holiday(25)
        data = md.to_dict()
        # Simulate JSON roundtrip
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        restored = MonthData.from_dict(restored_data)
        self.assertEqual(restored.year, 2026)
        self.assertEqual(restored.month, 3)
        self.assertEqual(restored.get_service("p1", 15), "s1")
        self.assertEqual(restored.get_service("p2", 16), "s2")
        self.assertEqual(restored.get_comment("p1"), "Comment")
        self.assertEqual(restored.get_note("p1", 15), "My note")
        self.assertIn(25, restored.holidays)


# ================================================================
# SCHEDULE CONTROLLER
# ================================================================
class TestScheduleController(unittest.TestCase):
    def setUp(self):
        self.ctrl = ScheduleController()
        self.svc_day = Service("Jour", "J", 12, "#A3D5FF")
        self.svc_night = Service("Nuit", "N", 12, "#FFD6A3")
        self.ctrl.services = [self.svc_day, self.svc_night]
        self.person = Person("Marie", "Dupont", 100)
        self.person2 = Person("Alice", "Martin", 80)
        self.ctrl.people = [self.person, self.person2]

    def test_apply_assignment_change(self):
        self.ctrl.apply_assignment_change(self.person.id, 15, self.svc_day.id, 2026, 1)
        md = self.ctrl.schedule.get((2026, 1))
        self.assertEqual(md.get_service(self.person.id, 15), self.svc_day.id)

    def test_apply_comment_change(self):
        self.ctrl.apply_comment_change(self.person.id, "Test", 2026, 1)
        md = self.ctrl.schedule.get((2026, 1))
        self.assertEqual(md.get_comment(self.person.id), "Test")

    def test_get_month_data_creates_if_missing(self):
        md = self.ctrl.get_month_data(2030, 6)
        self.assertIsNotNone(md)
        self.assertEqual(md.year, 2030)

    def test_get_person_by_id(self):
        self.assertEqual(self.ctrl.get_person_by_id(self.person.id), self.person)
        self.assertIsNone(self.ctrl.get_person_by_id("nonexistent"))

    def test_get_service_by_id(self):
        self.assertEqual(self.ctrl.get_service_by_id(self.svc_day.id), self.svc_day)
        self.assertIsNone(self.ctrl.get_service_by_id("nonexistent"))

    def test_add_recent_file(self):
        self.ctrl.add_recent_file("file1.mshift")
        self.ctrl.add_recent_file("file2.mshift")
        self.assertEqual(self.ctrl.recent_files[0], "file2.mshift")
        self.assertEqual(len(self.ctrl.recent_files), 2)

    def test_add_recent_file_deduplicates(self):
        self.ctrl.add_recent_file("file1.mshift")
        self.ctrl.add_recent_file("file2.mshift")
        self.ctrl.add_recent_file("file1.mshift")
        self.assertEqual(self.ctrl.recent_files[0], "file1.mshift")
        self.assertEqual(len(self.ctrl.recent_files), 2)

    def test_add_recent_file_limit(self):
        for i in range(10):
            self.ctrl.add_recent_file(f"file{i}.mshift")
        self.assertEqual(len(self.ctrl.recent_files), 5)

    def test_add_recent_file_empty(self):
        self.ctrl.add_recent_file("")
        self.assertEqual(len(self.ctrl.recent_files), 0)

    def test_ensure_builtin_services(self):
        self.ctrl.ensure_builtin_services()
        note_svc = next((s for s in self.ctrl.services if s.id == "builtin_note"), None)
        self.assertIsNotNone(note_svc)
        self.assertEqual(self.ctrl.services[-1].id, "builtin_note")

    def test_section_management(self):
        sec = Section(id="s1", label="Section 1")
        self.ctrl.sections = [sec]
        self.person.section_id = "s1"
        sec.add_person(self.person.id)
        result = self.ctrl.get_people_in_section("s1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, self.person.id)

    def test_move_person_to_section(self):
        sec1 = Section(id="s1", label="Sec1", people_ids=[self.person.id])
        sec2 = Section(id="s2", label="Sec2")
        self.ctrl.sections = [sec1, sec2]
        self.person.section_id = "s1"
        self.ctrl.move_person_to_section(self.person.id, "s2")
        self.assertEqual(self.person.section_id, "s2")
        self.assertNotIn(self.person.id, sec1.people_ids)
        self.assertIn(self.person.id, sec2.people_ids)

    def test_calculate_stats_for_month(self):
        md = self.ctrl.get_month_data(2026, 1)
        md.set_service(self.person.id, 1, self.svc_night.id)
        md.set_service(self.person.id, 2, self.svc_night.id)
        # 2026-01-03 is Saturday
        md.set_service(self.person.id, 3, self.svc_day.id)
        stats = self.ctrl.calculate_stats_for_month(self.person.id, 2026, 1)
        self.assertEqual(stats["night_count"], 2)
        sat, sun = stats["weekend_stats"]
        self.assertEqual(sat, 1)

    def test_apply_schema_to_month(self):
        schema = Schema("Test", start_weekday=0, span_days=7)
        schema.set_service(0, self.svc_day.id)  # Monday=Day
        schema.set_service(1, self.svc_night.id)  # Tuesday=Night
        self.ctrl.apply_schema_to_month(schema, self.person.id, 2026, 1)
        md = self.ctrl.get_month_data(2026, 1)
        # Check that at least some days got services applied
        has_day = any(md.get_service(self.person.id, d) == self.svc_day.id 
                      for d in range(1, 32))
        self.assertTrue(has_day)

    def test_apply_schema_no_overwrite(self):
        md = self.ctrl.get_month_data(2026, 1)
        md.set_service(self.person.id, 5, self.svc_night.id)
        schema = Schema("Test", start_weekday=0, span_days=7)
        for i in range(7):
            schema.set_service(i, self.svc_day.id)
        self.ctrl.apply_schema_to_month(schema, self.person.id, 2026, 1, overwrite=False)
        # Day 5 should NOT be overwritten
        self.assertEqual(md.get_service(self.person.id, 5), self.svc_night.id)

    def test_controller_serialization(self):
        self.ctrl.apply_assignment_change(self.person.id, 10, self.svc_day.id, 2026, 1)
        self.ctrl.last_year = 2026
        self.ctrl.last_month = 1
        data = self.ctrl.to_dict()
        self.assertIn("people", data)
        self.assertIn("services", data)
        self.assertEqual(data["last_year"], 2026)


# ================================================================
# RULES ENGINE
# ================================================================
class TestRulesEngine(unittest.TestCase):
    def setUp(self):
        self.svc_day = Service("Jour", "J", 12, "#A3D5FF")
        self.svc_night = Service("Nuit", "N", 12, "#FFD6A3")
        self.services_by_id = {self.svc_day.id: self.svc_day, self.svc_night.id: self.svc_night}
        self.people = [Person("P", str(i), 100) for i in range(5)]

    def test_no_violations_when_fully_staffed(self):
        md = MonthData(2026, 1)
        for d in range(1, 32):
            for i in range(3):
                md.set_service(self.people[i].id, d, self.svc_day.id)
        rule = StaffingRule("Jour", 3, ServiceKind.JOUR)
        violations = rule.evaluate(md, self.people, self.services_by_id, 2026, 1)
        self.assertEqual(len(violations), 0)

    def test_missing_violations(self):
        md = MonthData(2026, 1)
        # Only 1 person on day shift for day 1
        md.set_service(self.people[0].id, 1, self.svc_day.id)
        rule = StaffingRule("Jour", 3, ServiceKind.JOUR)
        violations = rule.evaluate(md, self.people, self.services_by_id, 2026, 1)
        day1_viol = [v for v in violations if v.day == 1]
        self.assertEqual(len(day1_viol), 1)
        self.assertEqual(day1_viol[0].severity, Severity.MISSING)
        self.assertEqual(day1_viol[0].count, 1)

    def test_excess_violations(self):
        md = MonthData(2026, 1)
        for i in range(5):
            md.set_service(self.people[i].id, 1, self.svc_day.id)
        rule = StaffingRule("Jour", 3, ServiceKind.JOUR)
        violations = rule.evaluate(md, self.people, self.services_by_id, 2026, 1)
        day1_viol = [v for v in violations if v.day == 1]
        self.assertEqual(day1_viol[0].severity, Severity.EXCESS)

    def test_violation_tooltip(self):
        md = MonthData(2026, 1)
        rule = StaffingRule("Jour", 3, ServiceKind.JOUR)
        violations = rule.evaluate(md, self.people, self.services_by_id, 2026, 1)
        self.assertIn("missing", violations[0].tooltip().lower())

    def test_evaluate_rules_combined(self):
        md = MonthData(2026, 1)
        violations = evaluate_rules(DEFAULT_RULES, md, self.people, self.services_by_id, 2026, 1)
        # Should have violations for every day (both Jour and Nuit missing)
        days_in_jan = 31
        self.assertEqual(len(violations), days_in_jan * 2)


# ================================================================
# PREFERENCES
# ================================================================
class TestPreferences(unittest.TestCase):
    def test_defaults(self):
        p = Preferences()
        self.assertEqual(p.previous_days_shown, 3)
        self.assertFalse(p.auto_save)
        self.assertEqual(p.drag_drop_mode, "swap")

    def test_serialization_roundtrip(self):
        p = Preferences(auto_save=True, row_height=60, column_width=50)
        data = p.to_dict()
        p2 = Preferences.from_dict(data)
        self.assertTrue(p2.auto_save)
        self.assertEqual(p2.row_height, 60)
        self.assertEqual(p2.column_width, 50)

    def test_all_fields_preserved(self):
        p = Preferences()
        data = p.to_dict()
        for field in ["previous_days_shown", "auto_save", "paste_overwrite_existing",
                       "copy_paste_mode", "drag_drop_mode", "row_height", "column_width",
                       "service_dropdown_display"]:
            self.assertIn(field, data)


# ================================================================
# UNDO MANAGER
# ================================================================
class TestUndoManager(unittest.TestCase):
    def test_push_and_undo(self):
        um = UndoManager(max_history=10)
        action = UndoableAction(name="test", undo_data="old", redo_data="new")
        um.push(action)
        self.assertTrue(um.can_undo())
        undone = um.undo()
        self.assertEqual(undone.undo_data, "old")
        self.assertFalse(um.can_undo())

    def test_redo(self):
        um = UndoManager(max_history=10)
        um.push(UndoableAction(name="test", undo_data="old", redo_data="new"))
        um.undo()
        self.assertTrue(um.can_redo())
        redone = um.redo()
        self.assertEqual(redone.redo_data, "new")

    def test_push_clears_redo(self):
        um = UndoManager(max_history=10)
        um.push(UndoableAction(name="a1", undo_data="1", redo_data="1"))
        um.push(UndoableAction(name="a2", undo_data="2", redo_data="2"))
        um.undo()
        self.assertTrue(um.can_redo())
        um.push(UndoableAction(name="a3", undo_data="3", redo_data="3"))
        self.assertFalse(um.can_redo())

    def test_max_history(self):
        um = UndoManager(max_history=3)
        for i in range(10):
            um.push(UndoableAction(name=f"a{i}", undo_data=i, redo_data=i))
        self.assertEqual(um.get_history_size(), 3)

    def test_clear(self):
        um = UndoManager()
        um.push(UndoableAction(name="test", undo_data="x", redo_data="x"))
        um.clear()
        self.assertFalse(um.can_undo())

    def test_descriptions(self):
        um = UndoManager()
        um.push(UndoableAction(name="My Action", undo_data="x", redo_data="x"))
        self.assertEqual(um.get_undo_description(), "My Action")
        um.undo()
        self.assertEqual(um.get_redo_description(), "My Action")

    def test_disable_enable(self):
        um = UndoManager()
        um.disable()
        um.push(UndoableAction(name="ignored", undo_data="x", redo_data="x"))
        self.assertFalse(um.can_undo())
        um.enable()
        um.push(UndoableAction(name="recorded", undo_data="x", redo_data="x"))
        self.assertTrue(um.can_undo())


class TestScheduleUndoManager(unittest.TestCase):
    def test_record_service_change(self):
        um = ScheduleUndoManager(max_history=10)
        um.record_service_change(2026, 1, 15, "p1", None, "s1")
        self.assertTrue(um.can_undo())
        action = um.undo()
        self.assertEqual(action.action_type, "service_change")

    def test_record_person_add(self):
        um = ScheduleUndoManager(max_history=10)
        um.record_person_add({"id": "p1", "prenom": "Marie", "nom": "Dupont"})
        self.assertTrue(um.can_undo())

    def test_record_person_delete(self):
        um = ScheduleUndoManager(max_history=10)
        um.record_person_delete({"id": "p1", "prenom": "Marie", "nom": "Dupont"})
        self.assertTrue(um.can_undo())

    def test_record_bulk_service_change(self):
        um = ScheduleUndoManager(max_history=10)
        changes = [
            {"year": 2026, "month": 1, "day": d, "person_id": "p1",
             "old_service_id": "s1", "new_service_id": None}
            for d in range(1, 6)
        ]
        um.record_bulk_service_change("Clear schedule", changes)
        self.assertTrue(um.can_undo())


# ================================================================
# FILE I/O
# ================================================================
class TestFileOperations(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.mshift', delete=False)
        self.temp_file.close()
        self.temp_path = self.temp_file.name

    def tearDown(self):
        if os.path.exists(self.temp_path):
            os.unlink(self.temp_path)
        # Clean up any backups
        base = os.path.splitext(self.temp_path)[0]
        import glob
        for f in glob.glob(f"{base}_backup_*"):
            os.unlink(f)

    def test_save_and_load_roundtrip(self):
        from file_io import save_schedule, load_schedule
        ctrl = ScheduleController()
        svc = Service("Jour", "J", 12, "#A3D5FF")
        person = Person("Marie", "Dupont", 100)
        ctrl.services = [svc]
        ctrl.people = [person]
        ctrl.sections = [Section(id="s1", label="Test", people_ids=[person.id])]
        ctrl.apply_assignment_change(person.id, 15, svc.id, 2026, 1)
        save_schedule(ctrl, self.temp_path)

        ctrl2 = ScheduleController()
        load_schedule(ctrl2, self.temp_path)
        self.assertEqual(len(ctrl2.people), 1)
        self.assertEqual(ctrl2.people[0].prenom, "Marie")
        test_svc = next((s for s in ctrl2.services if s.name == "Jour"), None)
        self.assertIsNotNone(test_svc)
        md = ctrl2.schedule.get((2026, 1))
        self.assertIsNotNone(md)

    def test_save_creates_file(self):
        from file_io import save_schedule
        if os.path.exists(self.temp_path):
            os.unlink(self.temp_path)
        ctrl = ScheduleController()
        save_schedule(ctrl, self.temp_path)
        self.assertTrue(os.path.exists(self.temp_path))

    def test_saved_file_is_valid_json(self):
        from file_io import save_schedule
        ctrl = ScheduleController()
        save_schedule(ctrl, self.temp_path)
        with open(self.temp_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn("people", data)
        self.assertIn("services", data)
        self.assertIn("schedule", data)

    def test_load_preserves_schedule_data(self):
        from file_io import save_schedule, load_schedule
        ctrl = ScheduleController()
        svc = Service("Nuit", "N", 12, "#FFD6A3")
        person = Person("Bob", "Test", 50)
        ctrl.services = [svc]
        ctrl.people = [person]
        ctrl.sections = [Section(id="s1", label="S1", people_ids=[person.id])]
        md = ctrl.get_month_data(2026, 3)
        md.set_service(person.id, 10, svc.id)
        md.set_comment(person.id, "Test comment")
        md.toggle_holiday(25)
        save_schedule(ctrl, self.temp_path)

        ctrl2 = ScheduleController()
        load_schedule(ctrl2, self.temp_path)
        md2 = ctrl2.schedule.get((2026, 3))
        self.assertIsNotNone(md2)
        self.assertEqual(md2.get_comment(person.id), "Test comment")
        self.assertIn(25, md2.holidays)


# ================================================================
# BUILD SAFETY
# ================================================================
class TestBuildSafety(unittest.TestCase):
    """
    Ensures that dev-only modules are never imported at the top level
    in production files. This prevents the built exe from crashing on
    launch due to missing modules that were excluded from the build.
    """

    # Modules that are excluded from the PyInstaller build
    DEV_ONLY_MODULES = {"dev_seed", "tests"}

    # Files that are themselves dev-only (don't need to be checked)
    DEV_ONLY_FILES = {"tests.py", "dev_seed.py"}

    def test_no_toplevel_dev_imports(self):
        """Check that no production .py file has a top-level import of a dev-only module."""
        import ast
        import glob

        project_dir = os.path.dirname(os.path.abspath(__file__))
        py_files = glob.glob(os.path.join(project_dir, "*.py"))

        violations = []

        for filepath in py_files:
            filename = os.path.basename(filepath)
            if filename in self.DEV_ONLY_FILES:
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=filename)
                except SyntaxError:
                    continue

            for node in ast.iter_child_nodes(tree):
                # Check 'import X' statements
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_root = alias.name.split(".")[0]
                        if module_root in self.DEV_ONLY_MODULES:
                            violations.append(
                                f"{filename}:{node.lineno} - "
                                f"top-level 'import {alias.name}' "
                                f"(dev-only module)"
                            )

                # Check 'from X import Y' statements
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_root = node.module.split(".")[0]
                        if module_root in self.DEV_ONLY_MODULES:
                            violations.append(
                                f"{filename}:{node.lineno} - "
                                f"top-level 'from {node.module} import ...' "
                                f"(dev-only module)"
                            )

        if violations:
            msg = (
                "Dev-only modules imported at top level in production files!\n"
                "These will crash the built exe. Move them inside conditional blocks.\n\n"
                + "\n".join(f"  ❌ {v}" for v in violations)
            )
            self.fail(msg)


# ================================================================
# APP STATE PERSISTENCE
# ================================================================
class TestAppState(unittest.TestCase):
    """
    Tests for the AppState class that manages app_state.json.
    This was completely untested and led to a bug where passing a
    non-dict to save_app_state corrupted the file, preventing launch.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = os.path.join(self.temp_dir, "app_state.json")
        
        # Create a patched AppState that uses our temp path
        from app_state import AppState
        self.app_state = AppState()
        self.app_state.get_app_state_path = lambda: self.temp_path

    def tearDown(self):
        if os.path.exists(self.temp_path):
            os.unlink(self.temp_path)
        os.rmdir(self.temp_dir)

    def test_save_and_load_roundtrip(self):
        """Basic save then load should return identical data."""
        data = {"people": [{"name": "Marie"}], "services": [], "last_year": 2026}
        self.app_state.save_app_state(data)
        loaded = self.app_state.load_app_state()
        self.assertEqual(loaded, data)

    def test_load_returns_none_when_no_file(self):
        """load_app_state should return None if file doesn't exist."""
        self.assertIsNone(self.app_state.load_app_state())

    def test_load_returns_none_on_empty_file(self):
        """An empty file (the exact bug scenario) should return None, not crash."""
        with open(self.temp_path, 'w') as f:
            pass  # Create empty file
        result = self.app_state.load_app_state()
        self.assertIsNone(result)

    def test_load_returns_none_on_corrupted_json(self):
        """Corrupted JSON should return None, not crash."""
        with open(self.temp_path, 'w') as f:
            f.write("{invalid json content!!!")
        result = self.app_state.load_app_state()
        self.assertIsNone(result)

    def test_load_returns_none_on_non_dict_json(self):
        """A JSON file containing a list or string should return None."""
        with open(self.temp_path, 'w') as f:
            json.dump(["not", "a", "dict"], f)
        result = self.app_state.load_app_state()
        self.assertIsNone(result)

    def test_save_rejects_non_dict(self):
        """save_app_state must reject non-dict arguments to prevent corruption."""
        # First save valid data
        valid_data = {"key": "value"}
        self.app_state.save_app_state(valid_data)
        
        # Try to save a non-dict (simulates the original bug: passing MainWindow)
        self.app_state.save_app_state("not a dict")
        
        # The original valid data should still be intact
        loaded = self.app_state.load_app_state()
        self.assertEqual(loaded, valid_data)

    def test_save_rejects_none(self):
        """save_app_state must reject None."""
        valid_data = {"key": "value"}
        self.app_state.save_app_state(valid_data)
        self.app_state.save_app_state(None)
        loaded = self.app_state.load_app_state()
        self.assertEqual(loaded, valid_data)

    def test_save_rejects_list(self):
        """save_app_state must reject list arguments."""
        valid_data = {"key": "value"}
        self.app_state.save_app_state(valid_data)
        self.app_state.save_app_state([1, 2, 3])
        loaded = self.app_state.load_app_state()
        self.assertEqual(loaded, valid_data)

    def test_controller_to_dict_is_json_serializable(self):
        """controller.to_dict() must produce data that json.dumps can serialize."""
        ctrl = ScheduleController()
        ctrl.services = [Service("Jour", "J", 12, "#A3D5FF")]
        ctrl.people = [Person("Marie", "Dupont", 100)]
        ctrl.sections = [Section(id="s1", label="Test", people_ids=[ctrl.people[0].id])]
        ctrl.apply_assignment_change(ctrl.people[0].id, 15, ctrl.services[0].id, 2026, 1)
        
        data = ctrl.to_dict()
        
        # Must be a dict
        self.assertIsInstance(data, dict)
        
        # Must be JSON-serializable (this would have caught the original bug)
        try:
            json_str = json.dumps(data)
        except (TypeError, ValueError) as e:
            self.fail(f"controller.to_dict() produced non-serializable data: {e}")
        
        # Must roundtrip through JSON
        restored = json.loads(json_str)
        self.assertIsInstance(restored, dict)
        self.assertIn("people", restored)
        self.assertIn("services", restored)

    def test_full_app_state_roundtrip(self):
        """Full integration: controller -> to_dict -> save -> load -> from_dict -> verify."""
        ctrl = ScheduleController()
        svc = Service("Jour", "J", 12, "#A3D5FF")
        person = Person("Marie", "Dupont", 100)
        ctrl.services = [svc]
        ctrl.people = [person]
        ctrl.sections = [Section(id="s1", label="Test", people_ids=[person.id])]
        ctrl.schemas = [Schema("Week", 0, 7)]
        ctrl.last_year = 2026
        ctrl.last_month = 3
        ctrl.apply_assignment_change(person.id, 15, svc.id, 2026, 3)
        
        # Save through AppState
        self.app_state.save_app_state(ctrl.to_dict())
        
        # Load and restore
        loaded = self.app_state.load_app_state()
        self.assertIsNotNone(loaded)
        
        ctrl2 = ScheduleController()
        ctrl2.from_dict(loaded)
        
        # Verify everything survived
        self.assertEqual(len(ctrl2.people), 1)
        self.assertEqual(ctrl2.people[0].prenom, "Marie")
        self.assertEqual(ctrl2.last_year, 2026)
        self.assertEqual(ctrl2.last_month, 3)
        self.assertTrue(any(s.name == "Jour" for s in ctrl2.services))
        self.assertEqual(len(ctrl2.schemas), 1)


# ================================================================
# SAVE_APP_STATE CALL SITE SAFETY (Static Analysis)
# ================================================================
class TestAppStateSaveCallSites(unittest.TestCase):
    """
    Static analysis test that scans all .py files to ensure every call 
    to save_app_state() passes .to_dict() as its argument.
    
    This catches the exact bug that corrupted app_state.json: calling
    save_app_state(self) or save_app_state(main_window) instead of
    save_app_state(self.controller.to_dict()).
    """

    def test_all_save_calls_use_to_dict(self):
        """Every save_app_state() call must pass .to_dict() as its argument."""
        import re
        import glob

        project_dir = os.path.dirname(os.path.abspath(__file__))
        py_files = glob.glob(os.path.join(project_dir, "*.py"))

        # Pattern matches: save_app_state(<anything>) on a line
        # We use a greedy match to capture everything including nested parens
        call_pattern = re.compile(r'save_app_state\((.+)\)')
        
        # Skip the definition line and test files
        skip_files = {"tests.py", "app_state.py"}

        violations = []

        for filepath in py_files:
            filename = os.path.basename(filepath)
            if filename in skip_files:
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    # Skip comments
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    
                    match = call_pattern.search(line)
                    if match:
                        argument = match.group(1).strip()
                        if ".to_dict()" not in argument:
                            violations.append(
                                f"{filename}:{lineno} - "
                                f"save_app_state({argument}) "
                                f"does NOT use .to_dict(). "
                                f"This will corrupt app_state.json!"
                            )

        if violations:
            msg = (
                "save_app_state() called with non-.to_dict() argument!\n"
                "This WILL corrupt app_state.json and prevent the app from launching.\n"
                "All calls must use: save_app_state(controller.to_dict())\n\n"
                + "\n".join(f"  ❌ {v}" for v in violations)
            )
            self.fail(msg)


# ================================================================
# TEST RUNNER
# ================================================================
def run_tests():
    print("=" * 70)
    print("Running MShift Test Suite")
    print("=" * 70)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestPersonModel,
        TestServiceModel,
        TestSectionModel,
        TestSchemaModel,
        TestSchemaAssignment,
        TestMonthData,
        TestScheduleController,
        TestRulesEngine,
        TestPreferences,
        TestUndoManager,
        TestScheduleUndoManager,
        TestFileOperations,
        TestBuildSafety,
        TestAppState,
        TestAppStateSaveCallSites,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print()
        print("[PASS] ALL TESTS PASSED!")
        print()
        return 0
    else:
        print()
        print("[FAIL] SOME TESTS FAILED")
        print()
        return 1


if __name__ == "__main__":
    import sys
    exit_code = run_tests()
    sys.exit(exit_code)
