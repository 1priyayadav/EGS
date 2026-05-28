from rest_framework import serializers
from emissions.models import EmissionRecord, ReviewEvent, RawIngestionRecord

class RawIngestionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawIngestionRecord
        fields = ['id', 'source_row_id', 'raw_payload', 'ingestion_status', 'received_at']

class ReviewEventSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = ReviewEvent
        fields = ['id', 'action_type', 'changed_by_username', 'timestamp', 'notes', 'before_payload', 'after_payload']

class EmissionRecordSerializer(serializers.ModelSerializer):
    raw_record = RawIngestionRecordSerializer(read_only=True)
    audit_history = ReviewEventSerializer(source='reviewevent_set', many=True, read_only=True)
    
    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'category', 'activity_type', 'status', 'validation_flags', 
            'auto_normalized_payload', 'analyst_corrected_payload', 'correction_reason',
            'normalization_assumptions', 'is_locked', 'raw_record', 'audit_history',
            'superseded_by', 'is_active_version', 'created_at', 'updated_at'
        ]

class EmissionRecordUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT', 'EDIT'])
    corrected_payload = serializers.JSONField(required=False, allow_null=True)
    correction_reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
