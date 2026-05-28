from django.db import models
from django.contrib.auth.models import User

class Tenant(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class TenantAwareModel(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    class Meta:
        abstract = True

class DataSource(TenantAwareModel):
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50, choices=[
        ('SAP', 'SAP'),
        ('UTILITY', 'Utility'),
        ('TRAVEL', 'Travel'),
    ])
    
    def __str__(self):
        return f"{self.name} ({self.source_type})"

class SourceFieldMapping(TenantAwareModel):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    source_field = models.CharField(max_length=255)
    normalized_field = models.CharField(max_length=255)
    transform_type = models.CharField(max_length=50, blank=True, null=True)
    required = models.BooleanField(default=False)
    default_unit = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.data_source.name}: {self.source_field} -> {self.normalized_field}"

class UnitConversionRule(models.Model):
    source_unit = models.CharField(max_length=50)
    normalized_unit = models.CharField(max_length=50)
    multiplier = models.FloatField()
    source_type = models.CharField(max_length=50)
    assumption_flag = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.source_unit} to {self.normalized_unit} (* {self.multiplier})"

class IngestionBatch(TenantAwareModel):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    source_file_name = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    checksum = models.CharField(max_length=255)
    batch_version = models.IntegerField(default=1)

    def __str__(self):
        return f"Batch {self.id} - {self.data_source.name} (v{self.batch_version})"

class RawIngestionRecord(TenantAwareModel):
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    source_row_id = models.CharField(max_length=255)
    raw_payload = models.JSONField()
    record_hash = models.CharField(max_length=255, unique=True)
    ingestion_status = models.CharField(max_length=50, choices=[
        ('PENDING_PARSING', 'Pending Parsing'),
        ('PARSED', 'Parsed'),
        ('FAILED', 'Failed')
    ], default='PENDING_PARSING')
    received_at = models.DateTimeField(auto_now_add=True)

class IngestionError(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    raw_record = models.ForeignKey(RawIngestionRecord, on_delete=models.CASCADE, null=True, blank=True)
    row_number = models.IntegerField(null=True, blank=True)
    raw_payload = models.JSONField(null=True, blank=True)
    error_type = models.CharField(max_length=255)
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

class EmissionRecord(TenantAwareModel):
    raw_record = models.OneToOneField(RawIngestionRecord, on_delete=models.CASCADE)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    
    category = models.CharField(max_length=50, choices=[
        ('SCOPE_1', 'Scope 1'),
        ('SCOPE_2', 'Scope 2'),
        ('SCOPE_3', 'Scope 3')
    ])
    activity_type = models.CharField(max_length=100)
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    billing_days = models.IntegerField(null=True, blank=True)
    
    raw_value = models.FloatField(null=True, blank=True)
    raw_unit = models.CharField(max_length=50, null=True, blank=True)
    normalized_value = models.FloatField(null=True, blank=True)
    
    auto_normalized_payload = models.JSONField()
    analyst_corrected_payload = models.JSONField(null=True, blank=True)
    correction_reason = models.TextField(null=True, blank=True)
    normalization_assumptions = models.JSONField(default=dict, blank=True)
    validation_flags = models.JSONField(default=list, blank=True)
    
    status = models.CharField(max_length=50, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('FLAGGED', 'Flagged')
    ], default='PENDING')
    
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    
    superseded_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    is_active_version = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ReviewEvent(models.Model):
    emission_record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50, choices=[
        ('CREATED', 'Created'),
        ('AUTO_NORMALIZED', 'Auto Normalized'),
        ('FLAGGED', 'Flagged'),
        ('EDITED', 'Edited'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SUPERSEDED', 'Superseded')
    ])
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)
    before_payload = models.JSONField(null=True, blank=True)
    after_payload = models.JSONField(null=True, blank=True)
