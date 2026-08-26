#!/usr/bin/env python3
"""Adversarial contract tests for the 742 mechanical visual review gate."""

from __future__ import annotations

import copy
import io
import json
import re
import unittest

from bind_742_review import mark_extended_visual_observations_reviewed
from validate_742_review import (
    EXPECTED_ID,
    EXTENDED_VISUAL_RENDER_CONTRACT,
    FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS,
    ROOT,
    SEPARATE_VISUAL_GATE_PATHS,
    _validate_extended_visual_semantics,
    read_owned_render_allowlist_records,
    validate_owned_render_semantic_coverage,
)


def fixture() -> tuple[dict, dict[str, dict]]:
    allowed: dict[str, dict] = {}
    observations = []
    for index, contract in enumerate(EXTENDED_VISUAL_RENDER_CONTRACT, start=1):
        artifact = {
            "path": contract["path"],
            "sha256": f"{index:02x}" * 32,
            "bytes": 1000 + index,
            "width_px": 1200,
            "height_px": 900,
            "provenance": "Deterministic render of the independently authored fixture.",
        }
        allowed[contract["path"]] = artifact
        observations.append({
            "semantic_id": contract["semantic_id"],
            "claim": contract["claim"],
            "observed": True,
            "artifact": {key: artifact[key] for key in ("path", "sha256", "bytes")},
        })
    record = {
        "schema_version": "2.0.0",
        "kind": "742-visual-gate-observation",
        "gate": "extended_visual_fidelity",
        "configuration_id": EXPECTED_ID,
        "candidate_tree_sha256": "PENDING",
        "reviewed_source_commit": "PENDING",
        "environment": {"renderer": "Blender fixture renderer", "os": None},
        "render_observations": observations,
        "boundary": (
            "Owned rendered presentation geometry only; no manufacturer geometry; "
            "reconstructed steering evidence is not factory steering or crab calibration."
        ),
    }
    return record, allowed


def validate_canonical_transition_state(record: dict, allowed: dict[str, dict]) -> str:
    """Accept one complete pending or reviewed state, never a mixed transition."""
    candidate = record.get("candidate_tree_sha256")
    commit = record.get("reviewed_source_commit")
    os_record = (record.get("environment") or {}).get("os")
    if candidate == "PENDING" and commit == "PENDING":
        if os_record is not None:
            raise RuntimeError("742 pending visual transition unexpectedly has an OS identity")
        _validate_extended_visual_semantics(record, allowed, expected_observed=False)
        return "pending"
    if re.fullmatch(r"[0-9a-f]{64}", str(candidate)) and re.fullmatch(r"[0-9a-f]{40}", str(commit)):
        if (
            set(os_record or {}) != {"name", "version", "build"}
            or not all(isinstance(value, str) and value.strip() for value in os_record.values())
        ):
            raise RuntimeError("742 reviewed visual transition lacks an exact OS identity")
        _validate_extended_visual_semantics(record, allowed, expected_observed=True)
        return "reviewed"
    raise RuntimeError("742 visual transition mixes pending and reviewed identity")


class ExtendedVisualSemanticsTests(unittest.TestCase):
    def assert_rejected(self, record: dict, allowed: dict[str, dict]) -> None:
        with self.assertRaises(RuntimeError):
            _validate_extended_visual_semantics(record, allowed)

    def test_complete_named_hash_bound_contract_passes(self) -> None:
        record, allowed = fixture()
        _validate_extended_visual_semantics(record, allowed)

    def test_owned_allowlist_requires_exact_named_semantic_coverage(self) -> None:
        _, allowed = fixture()
        for index, path in enumerate(sorted(SEPARATE_VISUAL_GATE_PATHS), start=20):
            allowed[path] = {"path": path, "sha256": f"{index:02x}" * 32, "bytes": index}
        validate_owned_render_semantic_coverage(allowed)
        allowed["docs/review/742/unreferenced-mechanism.png"] = {
            "path": "docs/review/742/unreferenced-mechanism.png", "sha256": "ff" * 32, "bytes": 1,
        }
        with self.assertRaises(RuntimeError):
            validate_owned_render_semantic_coverage(allowed)

    def test_capture_requirements_match_validator_contract_exactly(self) -> None:
        requirements = json.loads((ROOT / "docs/review/742/CAPTURE_REQUIREMENTS.json").read_text(encoding="utf-8"))
        self.assertEqual(
            requirements["extended_visual_fidelity"]["render_observations"],
            list(EXTENDED_VISUAL_RENDER_CONTRACT),
        )
        self.assertEqual(
            set(requirements["extended_visual_fidelity"]["forbidden_render_paths"]),
            FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS,
        )

    def test_source_correct_front_plan_is_required_and_limited_plan_is_forbidden(self) -> None:
        contract_paths = {item["path"] for item in EXTENDED_VISUAL_RENDER_CONTRACT}
        self.assertIn("docs/review/742/front-steering-plan.png", contract_paths)
        self.assertTrue(FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS.isdisjoint(contract_paths))
        self.assertFalse(any((ROOT / path).exists() for path in FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS))

    def test_superseded_front_plan_allowlist_entry_is_rejected(self) -> None:
        _, allowed = fixture()
        for index, path in enumerate(sorted(SEPARATE_VISUAL_GATE_PATHS), start=20):
            allowed[path] = {"path": path, "sha256": f"{index:02x}" * 32, "bytes": index}
        forbidden = next(iter(FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS))
        allowed[forbidden] = {"path": forbidden, "sha256": "ff" * 32, "bytes": 1}
        with self.assertRaises(RuntimeError):
            validate_owned_render_semantic_coverage(allowed)

    def test_committed_pending_template_is_structural_not_observed_evidence(self) -> None:
        allowed = read_owned_render_allowlist_records()
        validate_owned_render_semantic_coverage(allowed)
        record = json.loads((ROOT / "docs/review/742/extended-visual-fidelity.json").read_text(encoding="utf-8"))
        self.assertIn(validate_canonical_transition_state(record, allowed), {"pending", "reviewed"})

    def test_pending_state_rejects_an_observed_true_claim(self) -> None:
        record, allowed = fixture()
        with self.assertRaises(RuntimeError):
            _validate_extended_visual_semantics(record, allowed, expected_observed=False)

    def test_binder_marks_every_pending_render_observed(self) -> None:
        record, _ = fixture()
        for observation in record["render_observations"]:
            observation["observed"] = False
        mark_extended_visual_observations_reviewed(record)
        self.assertTrue(all(observation["observed"] is True for observation in record["render_observations"]))

    def test_binder_rejects_partial_review_without_mutating_pending_records(self) -> None:
        record, _ = fixture()
        for observation in record["render_observations"]:
            observation["observed"] = False
        record["render_observations"][4]["observed"] = True
        before = [observation["observed"] for observation in record["render_observations"]]
        with self.assertRaisesRegex(RuntimeError, "entirely pending"):
            mark_extended_visual_observations_reviewed(record)
        self.assertEqual(before, [observation["observed"] for observation in record["render_observations"]])

    def test_transition_accepts_one_complete_reviewed_state(self) -> None:
        record, allowed = fixture()
        record["candidate_tree_sha256"] = "a" * 64
        record["reviewed_source_commit"] = "b" * 40
        record["environment"]["os"] = {"name": "macOS", "version": "26.5.2", "build": "25F84"}
        self.assertEqual(validate_canonical_transition_state(record, allowed), "reviewed")

    def test_transition_rejects_mixed_identity(self) -> None:
        record, allowed = fixture()
        for observation in record["render_observations"]:
            observation["observed"] = False
        record["reviewed_source_commit"] = "b" * 40
        with self.assertRaisesRegex(RuntimeError, "mixes pending and reviewed"):
            validate_canonical_transition_state(record, allowed)

    def test_transition_rejects_partial_observation_in_each_identity_state(self) -> None:
        pending, allowed = fixture()
        for observation in pending["render_observations"]:
            observation["observed"] = False
        pending["render_observations"][2]["observed"] = True
        with self.assertRaises(RuntimeError):
            validate_canonical_transition_state(pending, allowed)

        reviewed, allowed = fixture()
        reviewed["candidate_tree_sha256"] = "a" * 64
        reviewed["reviewed_source_commit"] = "b" * 40
        reviewed["environment"]["os"] = {"name": "macOS", "version": "26.5.2", "build": "25F84"}
        reviewed["render_observations"][2]["observed"] = False
        with self.assertRaises(RuntimeError):
            validate_canonical_transition_state(reviewed, allowed)

    def test_transition_rejects_reviewed_state_without_exact_os_identity(self) -> None:
        record, allowed = fixture()
        record["candidate_tree_sha256"] = "a" * 64
        record["reviewed_source_commit"] = "b" * 40
        with self.assertRaisesRegex(RuntimeError, "exact OS identity"):
            validate_canonical_transition_state(record, allowed)

    def test_missing_circle_render_is_rejected(self) -> None:
        record, allowed = fixture()
        del record["render_observations"][6]
        self.assert_rejected(record, allowed)

    def test_missing_rear_linkage_render_is_rejected(self) -> None:
        record, allowed = fixture()
        del record["render_observations"][5]
        self.assert_rejected(record, allowed)

    def test_crab_render_cannot_reuse_circle_artifact(self) -> None:
        record, allowed = fixture()
        record["render_observations"][7]["artifact"] = copy.deepcopy(record["render_observations"][6]["artifact"])
        self.assert_rejected(record, allowed)

    def test_front_only_render_must_be_observed(self) -> None:
        record, allowed = fixture()
        record["render_observations"][8]["observed"] = False
        self.assert_rejected(record, allowed)

    def test_front_claim_cannot_omit_alignment_or_scrub_diagnostics(self) -> None:
        record, allowed = fixture()
        record["render_observations"][8]["claim"] = (
            "The visible FRONT label reports reconstructed front steering."
        )
        self.assert_rejected(record, allowed)

    def test_crab_claim_cannot_invent_an_icr_construction(self) -> None:
        record, allowed = fixture()
        record["render_observations"][7]["claim"] += " An actual ICR construction is visible."
        self.assert_rejected(record, allowed)

    def test_circle_claim_cannot_be_replaced_by_generic_visibility(self) -> None:
        record, allowed = fixture()
        record["render_observations"][6]["claim"] = "The render is visible."
        self.assert_rejected(record, allowed)

    def test_allowlisted_path_with_wrong_hash_is_rejected(self) -> None:
        record, allowed = fixture()
        record["render_observations"][5]["artifact"]["sha256"] = "ff" * 32
        self.assert_rejected(record, allowed)

    def test_extra_allowlisted_render_cannot_satisfy_gate_by_count(self) -> None:
        record, allowed = fixture()
        record["render_observations"].append(copy.deepcopy(record["render_observations"][-1]))
        self.assert_rejected(record, allowed)

    def test_factory_calibration_boundary_is_required(self) -> None:
        record, allowed = fixture()
        record["boundary"] = "Owned rendered presentation geometry only; no manufacturer geometry."
        self.assert_rejected(record, allowed)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ExtendedVisualSemanticsTests)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError(f"742 visual semantic tests failed: failures={len(result.failures)} errors={len(result.errors)}")
    print(json.dumps({
        "status": "PASS",
        "tests": result.testsRun,
        "mechanical_render_claims": len(EXTENDED_VISUAL_RENDER_CONTRACT),
    }, indent=2, sort_keys=True))
