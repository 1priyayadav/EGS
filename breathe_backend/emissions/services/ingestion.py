import csv
import json
import hashlib
from typing import List, Dict, Any
from emissions.models import DataSource, IngestionBatch, RawIngestionRecord, IngestionError, Tenant
from emissions.services.normalization import NormalizationService

class IngestionService:
    @staticmethod
    def _generate_record_hash(tenant_id: int, data_source_id: int, raw_payload: dict) -> str:
        payload_str = json.dumps(raw_payload, sort_keys=True)
        hash_input = f"{tenant_id}-{data_source_id}-{payload_str}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    @classmethod
    def ingest_csv(cls, tenant: Tenant, data_source: DataSource, file_obj, uploader, file_name: str) -> IngestionBatch:
        # Create Batch
        batch = IngestionBatch.objects.create(
            tenant=tenant,
            data_source=data_source,
            source_file_name=file_name,
            uploaded_by=uploader,
            checksum="csv_placeholder_checksum" # Could hash the file
        )
        
        decoded_file = file_obj.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        
        raw_records = []
        errors = []
        
        for row_number, row in enumerate(reader, start=1):
            record_hash = cls._generate_record_hash(tenant.id, data_source.id, row)
            
            # Superseding/Idempotency check: if hash exists, we could flag it or skip it.
            # Realistically, if we are doing a re-upload of a corrected batch, the payload hash
            # would be different for corrected rows. 
            if RawIngestionRecord.objects.filter(record_hash=record_hash).exists():
                continue
                
            raw_records.append(
                RawIngestionRecord(
                    tenant=tenant,
                    batch=batch,
                    data_source=data_source,
                    source_row_id=str(row_number),
                    raw_payload=row,
                    record_hash=record_hash,
                    ingestion_status='PENDING_PARSING'
                )
            )
            
        if raw_records:
            RawIngestionRecord.objects.bulk_create(raw_records)
            
        # Trigger Normalization
        NormalizationService.process_batch(batch)
        return batch

    @classmethod
    def ingest_json(cls, tenant: Tenant, data_source: DataSource, payload: List[Dict[str, Any]], uploader) -> IngestionBatch:
        batch = IngestionBatch.objects.create(
            tenant=tenant,
            data_source=data_source,
            source_file_name="API_Webhook",
            uploaded_by=uploader,
            checksum="json_placeholder_checksum"
        )
        
        raw_records = []
        for index, item in enumerate(payload):
            record_hash = cls._generate_record_hash(tenant.id, data_source.id, item)
            
            if RawIngestionRecord.objects.filter(record_hash=record_hash).exists():
                continue
                
            raw_records.append(
                RawIngestionRecord(
                    tenant=tenant,
                    batch=batch,
                    data_source=data_source,
                    source_row_id=item.get('id', str(index)),
                    raw_payload=item,
                    record_hash=record_hash,
                    ingestion_status='PENDING_PARSING'
                )
            )
            
        if raw_records:
            RawIngestionRecord.objects.bulk_create(raw_records)
            
        NormalizationService.process_batch(batch)
        return batch
