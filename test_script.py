"""
INF1103 Team 4 | Campus Safety Hazard Reporting System
Procedural-only offline test script (34 tests; no class definitions).

Run:
    python test_script.py
    python test_script.py --details
    python test_script.py --no-data

All API calls are mocked. Database tests use a fresh temporary JSON file.
Console output is delegated to IO_Manager.display_message().
"""

import argparse
import json
import logging
import os
import sys
import tempfile
import time
import traceback
from functools import wraps
from pathlib import Path
from typing import Callable
from unittest.mock import patch

import ai_manager
import Data_Manager
import IO_Manager
import logic_manager
import main


# Hardcoded sample Gemini response; no live API requests.
VALID_ASSESSMENT = {
    "risk_summary": "Wet floor could cause a slip.",
    "category": "Plumbing",
    "severity": "High",
    "operational_impact": "Moderate",
    "contextual_insights": "Request staff inspection and appropriate precautions.",
}


def sample_record() -> dict[str, object]:
    """Create independent fake input data for each test."""
    return {
        "reporter_name": "Test Reporter",
        "reporter_contact": "test@example.invalid",
        "location": "SIT E6",
        "impact_headcount": 100,
        "asset_info": "Wet floor",
        "description": "Wet floor near the corridor, requiring inspection.",
        "image_patch": "",
        "visual_evidence_path": "",
        "status": "Pending Review",
    }


def isolated_db(test_fn: Callable[[str], None]) -> Callable[[], None]:
    """Run one database test against its own temporary JSON database."""
    @wraps(test_fn)
    def wrapped() -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "test_incidents.json")
            # Override BOTH the configured path and the accessor.
            with patch.dict(os.environ, {"INCIDENTS_DB": db_path}), \
                 patch.object(Data_Manager, "get_db_path", return_value=db_path):
                assert Path(Data_Manager.get_db_path()).resolve() == Path(db_path).resolve()
                test_fn(db_path)
    return wrapped


# AI MANAGER TESTS

def test_valid_ai_assessment_is_accepted():
    assert ai_manager.validate_response(VALID_ASSESSMENT)

def test_missing_required_field_is_rejected():
    assessment = dict(VALID_ASSESSMENT)
    assessment.pop('risk_summary')
    assert not ai_manager.validate_response(assessment)

def test_invalid_category_is_rejected():
    assessment = dict(VALID_ASSESSMENT, category='Unknown Category')
    assert not ai_manager.validate_response(assessment)

def test_invalid_severity_is_rejected():
    assessment = dict(VALID_ASSESSMENT, severity='Extreme')
    assert not ai_manager.validate_response(assessment)

def test_invalid_impact_is_rejected():
    assessment = dict(VALID_ASSESSMENT, operational_impact='Huge')
    assert not ai_manager.validate_response(assessment)

def test_non_string_field_is_rejected():
    assessment = dict(VALID_ASSESSMENT, risk_summary=123)
    assert not ai_manager.validate_response(assessment)

def test_parse_valid_json():
    assert ai_manager.parse_response(json.dumps(VALID_ASSESSMENT)) == VALID_ASSESSMENT

def test_parse_markdown_fenced_json():
    response = '```json\n' + json.dumps(VALID_ASSESSMENT) + '\n```'
    assert ai_manager.parse_response(response) == VALID_ASSESSMENT

def test_parse_invalid_json():
    assert ai_manager.parse_response('not JSON') is None

def test_prompt_excludes_reporter_identity():
    prompt = ai_manager.build_prompt(sample_record())
    assert 'SIT E6' in prompt
    assert 'Wet floor' in prompt
    assert 'Test Reporter' not in prompt
    assert 'test@example.invalid' not in prompt

def test_missing_image_returns_no_image():
    assert ai_manager.encode_image(None) == (None, None)

def test_unsupported_image_format_is_rejected():
    with tempfile.TemporaryDirectory() as directory:
        image = Path(directory) / 'evidence.gif'
        image.write_bytes(b'simulated image data')
        assert ai_manager.encode_image(str(image)) == (None, None)

def test_api_without_key_returns_controlled_error():
    with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
        result = json.loads(ai_manager.call_api('Example report'))
    assert 'error' in result

def test_api_success_without_network():
    """Mock the Gemini client so this test never contacts Google."""
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key-not-real'}):
        with patch.object(ai_manager.genai, 'Client') as mock_client:
            client = mock_client.return_value.__enter__.return_value
            client.models.generate_content.return_value.text = json.dumps(VALID_ASSESSMENT)
            response = ai_manager.call_api('Example hazard description')
            assert json.loads(response) == VALID_ASSESSMENT
            client.models.generate_content.assert_called_once()

# LOGIC MANAGER TESTS

def test_score_for_high_moderate_hazard():
    report: dict[str, str | int] = {'severity': 'High', 'operational_impact': 'Moderate', 'historical_frequency': 0}
    assert logic_manager.score(report) == 6

def test_high_severity_triggers_high_priority():
    report: dict[str, str | int] = {'severity': 'High', 'operational_impact': 'Moderate', 'historical_frequency': 0}
    decision = logic_manager.evaluate(report)
    assert decision['score'] == 6
    assert decision['priority'] == 'High'
    assert decision['route'] == 'Priority Maintenance Queue'

def test_critical_severity_and_severe_impact():
    report: dict[str, str | int] = {'severity': 'Critical', 'operational_impact': 'Severe', 'historical_frequency': 0}
    decision = logic_manager.evaluate(report)
    assert decision['priority'] == 'Critical'
    assert decision['route'] == 'Urgent Emergency Dispatch'

def test_low_severity_and_minor_impact():
    report: dict[str, str | int] = {'severity': 'Low', 'operational_impact': 'Minor', 'historical_frequency': 0}
    assert logic_manager.evaluate(report)['priority'] == 'Normal'

def test_historical_frequency_case_insensitive():
    report = {'location': 'sit e6', 'asset_info': 'wet floor'}
    previous = [{'location': 'SIT E6', 'asset_info': 'Wet Floor'}, {'location': 'SIT E6', 'asset_info': 'Aircon'}, {'location': 'SIT E6', 'asset_info': 'wet floor'}]
    assert logic_manager.calculate_historical_frequency(report, previous) == 2

def test_duplicate_pending_report():
    report = {'location': 'sit e6', 'asset_info': 'wet floor'}
    previous = [{'incident_id': 'INCIDENT-003', 'location': 'SIT E6', 'asset_info': 'Wet Floor', 'status': 'Pending Review'}]
    result = logic_manager.check_duplicate(report, previous)
    assert 'INCIDENT-003' in result

def test_resolved_incident_is_not_active_duplicate():
    report = {'location': 'SIT E6', 'asset_info': 'Wet floor'}
    previous = [{'incident_id': 'INCIDENT-002', 'location': 'SIT E6', 'asset_info': 'Wet floor', 'status': 'Resolved'}]
    assert logic_manager.check_duplicate(report, previous) == 'Unique'

def test_offline_fallback_when_ai_returns_error():
    with patch.object(logic_manager, 'call_api', return_value='{"error": "unavailable"}'):
        result = logic_manager.process_record(sample_record())
    assert '[Offline Assessment]' in result['risk_summary']
    assert result['severity'] == 'Medium'
    assert result['operational_impact'] == 'Moderate'

def test_valid_mocked_ai_response_used():
    with patch.object(logic_manager, 'call_api', return_value=json.dumps(VALID_ASSESSMENT)):
        result = logic_manager.process_record(sample_record())
    assert result == VALID_ASSESSMENT

# DATA MANAGER TESTS

@isolated_db
def test_initial_database_is_empty(db_path: str):
    assert db_path
    assert Data_Manager.load() == []

@isolated_db
def test_save_then_load_preserves_reporter_name(db_path: str):
    assert db_path
    report = sample_record()
    report.update(VALID_ASSESSMENT)
    assert Data_Manager.save(report)
    stored = Data_Manager.load()
    assert len(stored) == 1
    assert stored[0]['reporter_name'] == 'Test Reporter'
    assert stored[0]['severity'] == 'High'
    assert stored[0]['incident_id'] == 'INCIDENT-001'

@isolated_db
def test_incident_ids_are_sequential(db_path: str):
    assert db_path
    first = sample_record()
    second = sample_record()
    assert Data_Manager.save(first)
    assert Data_Manager.save(second)
    assert first['incident_id'] == 'INCIDENT-001'
    assert second['incident_id'] == 'INCIDENT-002'

@isolated_db
def test_update_status(db_path: str):
    assert db_path
    report = sample_record()
    assert Data_Manager.save(report)
    incident_id = report['incident_id']
    assert isinstance(incident_id, str)
    assert Data_Manager.update_incident_status(incident_id, 'Resolved')
    assert Data_Manager.load()[0]['status'] == 'Resolved'

@isolated_db
def test_delete_incident(db_path: str):
    assert db_path
    report = sample_record()
    assert Data_Manager.save(report)
    incident_id = report['incident_id']
    assert isinstance(incident_id, str)
    assert Data_Manager.delete_incident_by_id(incident_id)
    assert Data_Manager.load() == []

@isolated_db
def test_corrupt_json_database_is_detected(db_path: str):
    assert db_path
    Path(db_path).write_text('not valid JSON', encoding='utf-8')
    assert Data_Manager.load() == []
    assert Data_Manager.last_load_warning

# IO MANAGER TESTS

def test_confirm_yes():
    with patch('builtins.input', return_value='y'), patch('builtins.print'):
        assert IO_Manager.confirm_submission()

def test_cancel_no():
    with patch('builtins.input', return_value='n'), patch('builtins.print'):
        assert not IO_Manager.confirm_submission()

def test_invalid_answer_then_yes():
    with patch('builtins.input', side_effect=['maybe', 'y']), patch('builtins.print'):
        assert IO_Manager.confirm_submission()

# MAIN WORKFLOW TESTS


def submit_with_mocks(confirm: bool):
    """
    Simulates hazard report submission using mocked dependencies.
    Tests the submission workflow without calling Gemini
    or modifying the actual incident database.
    """

    report = sample_record()

    # Mock all external interactions and database operations
    with (
        patch.object(
            main.IO_Manager, "get_user_input",
            return_value=report
        ),
        patch.object(main.IO_Manager, "display_workflow_header"),
        patch.object(main.IO_Manager, "display_message"),
        patch.object(main.IO_Manager, "display_priority_calculation"),
        patch.object(main.IO_Manager, "display_pre_submission_summary"),
        patch.object(
            main.IO_Manager, "confirm_submission",
            return_value=confirm
        ),
        patch.object(main.IO_Manager, "display_submission_success"),
        patch.object(main.IO_Manager, "display_incident_result"),
        patch.object(main.Data_Manager, "load", return_value=[]),
        patch.object(main.Data_Manager, "last_load_warning", ""),
        patch.object(
            main.Data_Manager, "save",
            return_value=True
        ) as mock_save,
        patch.object(
            main, "run_ai_assessment",
            return_value=(dict(VALID_ASSESSMENT), "Gemini AI")
        ),
    ):
        main.submit_hazard_report()

        return mock_save.call_count, report

def test_cancel_does_not_save():
    saves, report = submit_with_mocks(False)
    assert saves == 0
    assert report['final_priority'] == 'High'

def test_confirm_saves_one_complete_record():
    saves, report = submit_with_mocks(True)
    assert saves == 1
    assert report['severity'] == 'High'
    assert report['final_priority'] == 'High'
    assert report['assessment_source'] == 'Gemini AI'


# Group functions instead of TestCase classes to maintain procedural code.
TEST_GROUPS = (
    ('AI Manager', (test_valid_ai_assessment_is_accepted, test_missing_required_field_is_rejected, test_invalid_category_is_rejected, test_invalid_severity_is_rejected, test_invalid_impact_is_rejected, test_non_string_field_is_rejected, test_parse_valid_json, test_parse_markdown_fenced_json, test_parse_invalid_json, test_prompt_excludes_reporter_identity, test_missing_image_returns_no_image, test_unsupported_image_format_is_rejected, test_api_without_key_returns_controlled_error, test_api_success_without_network,)),
    ('Logic Manager', (test_score_for_high_moderate_hazard, test_high_severity_triggers_high_priority, test_critical_severity_and_severe_impact, test_low_severity_and_minor_impact, test_historical_frequency_case_insensitive, test_duplicate_pending_report, test_resolved_incident_is_not_active_duplicate, test_offline_fallback_when_ai_returns_error, test_valid_mocked_ai_response_used,)),
    ('Data Manager', (test_initial_database_is_empty, test_save_then_load_preserves_reporter_name, test_incident_ids_are_sequential, test_update_status, test_delete_incident, test_corrupt_json_database_is_detected,)),
    ('IO Manager', (test_confirm_yes, test_cancel_no, test_invalid_answer_then_yes,)),
    ('Main Workflow', (test_cancel_does_not_save, test_confirm_saves_one_complete_record,)),
 )


def run_tests(show_details: bool = False, include_data: bool = True):
    """Execute offline tests and display the grouped result through IO_Manager."""
    width = 74
    emit = IO_Manager.display_message
    emit("=" * width)
    emit("  INF1103 | CAMPUS SAFETY HAZARD REPORTING SYSTEM")
    emit("  AUTOMATED TEST REPORT - OFFLINE")
    emit("=" * width)
    emit(f"  {'MODULE':<22}{'PASSED':>9}{'TOTAL':>9}{'STATUS':>12}{'TIME':>11}")
    emit("-" * width)

    total = passed = failures = 0
    started = time.perf_counter()
    previous_log_level = logging.root.manager.disable
    try:
        # Failure-scenario logs are expected; test failures still appear below.
        logging.disable(logging.CRITICAL)
        for group_name, functions in TEST_GROUPS:
            if not include_data and group_name == "Data Manager":
                continue
            group_pass = 0
            group_fails: list[tuple[str, str]] = []
            group_start = time.perf_counter()
            for check in functions:
                total += 1
                try:
                    check()
                    group_pass += 1
                    passed += 1
                    if show_details:
                        emit(f"    {check.__name__} ... PASS")
                except Exception:
                    failures += 1
                    group_fails.append((check.__name__, traceback.format_exc()))
                    if show_details:
                        emit(f"    {check.__name__} ... FAIL")
            elapsed = time.perf_counter() - group_start
            count = len(functions)
            status = "PASS" if group_pass == count else "FAIL"
            emit(
                f"  {group_name:<22}{group_pass:>9}{count:>9}"
                f"{status:>12}{elapsed:>10.3f}s"
            )
            for case_name, error in group_fails:
                emit(f"\n  FAILURE: {case_name}\n{error}")
            if show_details or group_fails:
                emit("-" * width)
    finally:
        logging.disable(previous_log_level)

    elapsed = time.perf_counter() - started
    successful = total > 0 and passed == total and failures == 0
    emit("-" * width)
    emit(
        f"  {'TOTAL':<22}{passed:>9}{total:>9}"
        f"{('PASS' if successful else 'FAIL'):>12}{elapsed:>10.3f}s"
    )
    emit(f"  Failures: {failures}   Errors: 0   Skipped: 0")
    emit("=" * width)
    emit(f"  RESULT: {'ALL ' + str(passed) + ' TESTS PASSED' if successful else 'TESTS NEED ATTENTION'}")
    if not include_data:
        emit("  Note: Data Manager tests excluded (--no-data).")
    emit("=" * width)
    return successful


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run procedural INF1103 offline tests")
    parser.add_argument("--details", action="store_true", help="Show every test result")
    parser.add_argument("--no-data", action="store_true", help="Exclude six database tests")
    options = parser.parse_args()
    sys.exit(0 if run_tests(options.details, not options.no_data) else 1)