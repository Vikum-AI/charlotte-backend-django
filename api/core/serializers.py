from rest_framework import serializers

from api.core.tasks.evidence_extraction_tasks import extract_data_from_evidence


class EvidenceUploadSerializer(serializers.Serializer):
    evidence_link = serializers.URLField(write_only=True)
    case_id = serializers.CharField(write_only=True, required=True)
    message = serializers.CharField(read_only=True)

    def create(self, validated_data):
        extraction_link = validated_data.pop('evidence_link')
        extract_data_from_evidence.send(validated_data['case_id'], extraction_link)

        validated_data['message'] = 'Evidence extraction queueed successfully'
        return validated_data
