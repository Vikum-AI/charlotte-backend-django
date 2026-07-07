from rest_framework import serializers

from api.core.tasks.evidence_extraction_tasks import extract_data_from_evidence
from api.core.utils.rule_engine.validation import (
    ConditionValidationError,
    validate_condition_tree,
)


class EvidenceUploadSerializer(serializers.Serializer):
    evidence_link = serializers.URLField(write_only=True, required=False)
    file_url = serializers.URLField(write_only=True, required=False)
    file_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True)
    evidence_type_hint = serializers.ChoiceField(
        choices=("approval", "kyc_status", "custom"),
        write_only=True,
        required=False,
    )
    field_path = serializers.CharField(
        write_only=True, required=False, allow_blank=True)
    extracted_value = serializers.CharField(
        write_only=True, required=False, allow_blank=True)
    case_id = serializers.CharField(write_only=True, required=True)
    message = serializers.CharField(read_only=True)

    def validate(self, attrs):
        evidence_link = attrs.get("file_url") or attrs.get("evidence_link")

        if not evidence_link:
            raise serializers.ValidationError(
                {"file_url": "Either file_url or evidence_link is required."}
            )

        if attrs.get("evidence_type_hint") == "custom":
            if not attrs.get("field_path"):
                raise serializers.ValidationError(
                    {"field_path": "field_path is required for custom evidence."}
                )

            if not attrs.get("extracted_value"):
                raise serializers.ValidationError(
                    {"extracted_value": "extracted_value is required for custom evidence."}
                )

        return attrs

    def create(self, validated_data):
        extraction_link = validated_data.get(
            "file_url") or validated_data.get("evidence_link")
        evidence_metadata = {
            "file_url": extraction_link,
            "file_key": validated_data.get("file_key"),
            "evidence_type_hint": validated_data.get("evidence_type_hint"),
            "field_path": validated_data.get("field_path"),
            "extracted_value": validated_data.get("extracted_value"),
        }

        evidence_metadata = {
            key: value for key, value in evidence_metadata.items() if value not in (None, "")
        }

        extract_data_from_evidence.send(
            validated_data["case_id"],
            extraction_link,
            evidence_metadata,
        )

        validated_data["message"] = "Evidence extraction queued successfully"
        return validated_data


class CaseCreateSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()
    assigned_to = serializers.CharField(
        required=False, allow_null=True, allow_blank=True)


class CaseDetailResponseSerializer(serializers.Serializer):
    case = serializers.JSONField()
    graph = serializers.JSONField()
    rules = serializers.ListField(child=serializers.JSONField())


class CaseRuleCreateSerializer(serializers.Serializer):
    rule_id = serializers.CharField()
    definition = serializers.JSONField()

    def validate_definition(self, value):
        try:
            validate_condition_tree(value)
        except ConditionValidationError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value


class AddSuggestedEvidenceSerializer(serializers.Serializer):
    suggested_evidence_id = serializers.CharField()


class SuggestedEvidenceResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    evidence_type = serializers.CharField()
    file_url = serializers.URLField()
    field_path = serializers.CharField()
    suggested_condition = serializers.JSONField()
    already_added = serializers.BooleanField()


class SuggestedSubRuleResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    tier = serializers.CharField()
    condition_type = serializers.CharField()
    condition_fragment = serializers.JSONField()


class ConfirmEvidenceSerializer(serializers.Serializer):
    confirmed_by_user_id = serializers.CharField()
