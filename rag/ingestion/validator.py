"""Validator for data authority rules, conflict checking, and record schemas.
"""
from typing import Dict, List, Any, Tuple

REQUIRED_RECORD_FIELDS = {"id", "category", "source_type", "verified", "status"}
VALID_SOURCE_TYPES = {"business_provided", "external_reference", "hackathon_assumption", "unknown"}

class DataValidator:
    @staticmethod
    def validate_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate an individual data record according to authority rules."""
        errors = []
        for field in REQUIRED_RECORD_FIELDS:
            if field not in record:
                errors.append(f"Missing required field: '{field}' in record {record.get('id', 'unknown')}")

        source_type = record.get("source_type")
        verified = record.get("verified")

        if source_type not in VALID_SOURCE_TYPES:
            errors.append(f"Invalid source_type '{source_type}'. Expected one of {VALID_SOURCE_TYPES}")

        # Rule: Type 1 must have verified = True
        if source_type == "business_provided" and verified is not True:
            errors.append(f"Record {record.get('id')}: Type 1 (business_provided) must have verified=True")

        # Rule: Type 2 must have verified = False
        if source_type == "external_reference" and verified is not False:
            errors.append(f"Record {record.get('id')}: Type 2 (external_reference) must have verified=False")

        # Rule: Type 3 must have verified = False
        if source_type == "hackathon_assumption" and verified is not False:
            errors.append(f"Record {record.get('id')}: Type 3 (hackathon_assumption) must have verified=False")

        # Rule: Unknown/TBD must have verified = False
        if source_type == "unknown" and verified is not False:
            errors.append(f"Record {record.get('id')}: unknown/TBD record must have verified=False")

        return len(errors) == 0, errors

    @staticmethod
    def validate_conflict(conflict: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate conflict metadata entries."""
        required = {"field", "business_provided", "external_reference", "status", "customer_answer", "reason"}
        errors = []
        for f in required:
            if f not in conflict:
                errors.append(f"Conflict record missing required field '{f}'")
        if conflict.get("status") != "CONFLICT":
            errors.append(f"Conflict record status must be 'CONFLICT', got '{conflict.get('status')}'")
        return len(errors) == 0, errors

    @classmethod
    def validate_dataset(cls, records: List[Dict[str, Any]], conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate complete dataset and return summary."""
        record_errors = []
        conflict_errors = []
        type_counts = {"business_provided": 0, "external_reference": 0, "hackathon_assumption": 0, "unknown": 0}

        for rec in records:
            valid, errs = cls.validate_record(rec)
            if not valid:
                record_errors.extend(errs)
            st = rec.get("source_type", "unknown")
            type_counts[st] = type_counts.get(st, 0) + 1

        for conf in conflicts:
            valid, errs = cls.validate_conflict(conf)
            if not valid:
                conflict_errors.extend(errs)

        is_valid = len(record_errors) == 0 and len(conflict_errors) == 0
        return {
            "valid": is_valid,
            "total_records": len(records),
            "type_counts": type_counts,
            "total_conflicts": len(conflicts),
            "record_errors": record_errors,
            "conflict_errors": conflict_errors
        }
