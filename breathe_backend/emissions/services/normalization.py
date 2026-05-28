import datetime
from django.db import transaction
from emissions.models import RawIngestionRecord, EmissionRecord, SourceFieldMapping, UnitConversionRule, ReviewEvent

class NormalizationService:
    @classmethod
    def process_batch(cls, batch):
        raw_records = RawIngestionRecord.objects.filter(batch=batch, ingestion_status='PENDING_PARSING')
        
        # Prefetch mappings to avoid N+1
        mappings = SourceFieldMapping.objects.filter(data_source=batch.data_source)
        mapping_dict = {m.source_field: m for m in mappings}
        
        for raw in raw_records:
            cls._normalize_record(raw, mapping_dict)
            
    @classmethod
    @transaction.atomic
    def _normalize_record(cls, raw_record, mapping_dict):
        payload = raw_record.raw_payload
        normalized_data = {}
        assumptions = {}
        flags = []
        
        # 1. Dynamic Field Mapping
        for source_key, value in payload.items():
            if source_key in mapping_dict:
                mapping = mapping_dict[source_key]
                norm_key = mapping.normalized_field
                
                # Simple type casting based on transform_type could go here
                parsed_value = value
                if mapping.transform_type == 'float':
                    try:
                        parsed_value = float(value)
                    except (ValueError, TypeError):
                        flags.append(f"Invalid float for {source_key}: {value}")
                        parsed_value = 0.0
                
                normalized_data[norm_key] = parsed_value
                
                if mapping.default_unit and 'raw_unit' not in normalized_data:
                    normalized_data['raw_unit'] = mapping.default_unit
                    assumptions['unit'] = f"Assumed default unit {mapping.default_unit} from mapping"
            else:
                # If a field isn't mapped, we can retain it in an 'unmapped' dict or just ignore
                pass
                
        # Fill in missing required mapped fields
        for source_key, mapping in mapping_dict.items():
            if mapping.required and mapping.normalized_field not in normalized_data:
                flags.append(f"Missing required mapped field: {mapping.normalized_field}")
                
        # 2. Extract Core Fields depending on source type
        source_type = raw_record.data_source.source_type
        
        category = 'SCOPE_3'
        activity_type = 'Unknown'
        raw_value = normalized_data.get('raw_value', 0.0)
        raw_unit = normalized_data.get('raw_unit', '')
        
        if source_type == 'SAP':
            category = 'SCOPE_1'
            activity_type = 'Fuel'
            # Heuristics for SAP
            if not normalized_data.get('plant_code'):
                flags.append("unknown plant code")
            if raw_value < 0:
                flags.append("negative fuel quantity")
                
        elif source_type == 'UTILITY':
            category = 'SCOPE_2'
            activity_type = 'Electricity'
            # Heuristics for Utility
            if not normalized_data.get('meter_id'):
                flags.append("missing meter ID")
            # Spike check and overlapping periods would require querying past records.
            # Simplified for prototype:
            
        elif source_type == 'TRAVEL':
            category = 'SCOPE_3'
            activity_type = normalized_data.get('travel_type', 'Flight')
            # Heuristics for Travel
            if activity_type == 'Flight':
                origin = normalized_data.get('origin_airport')
                dest = normalized_data.get('destination_airport')
                if not origin or not dest:
                    flags.append("impossible airport pair")
                else:
                    # Dummy great-circle lookup
                    if origin == 'XXX' or dest == 'XXX':
                        flags.append("impossible airport pair")
                    else:
                        # Estimate distance
                        normalized_data['raw_value'] = 500.0 # Placeholder distance in km
                        assumptions['distance'] = f"Estimated distance between {origin} and {dest}"
            
            if 'traveler_email' not in normalized_data:
                flags.append("missing traveler information")
                
        # 3. Unit Conversion
        normalized_value = raw_value
        if raw_unit:
            try:
                conversion = UnitConversionRule.objects.get(
                    source_unit__iexact=raw_unit, 
                    source_type=source_type
                )
                normalized_value = float(raw_value) * conversion.multiplier
                if conversion.assumption_flag:
                    assumptions['conversion'] = "Unit conversion was flagged as an assumption"
            except UnitConversionRule.DoesNotExist:
                flags.append("impossible unit conversion")
        
        status = 'FLAGGED' if flags else 'PENDING'
        
        # 4. Handle Superseding Logic
        # For simplicity in prototype, if we find an existing record with the same deduplication keys
        # (like same meter_id and billing period, or same traveler and flight details), we supersede it.
        # Here we do a basic lookup based on source_row_id (if it acts as a unique external ID)
        superseded_record = EmissionRecord.objects.filter(
            data_source=raw_record.data_source,
            raw_record__source_row_id=raw_record.source_row_id,
            is_active_version=True
        ).first()

        # 5. Create EmissionRecord
        record = EmissionRecord.objects.create(
            tenant=raw_record.tenant,
            data_source=raw_record.data_source,
            raw_record=raw_record,
            category=category,
            activity_type=activity_type,
            raw_value=raw_value,
            raw_unit=raw_unit,
            normalized_value=normalized_value,
            auto_normalized_payload=normalized_data,
            normalization_assumptions=assumptions,
            validation_flags=flags,
            status=status
        )
        
        if superseded_record:
            superseded_record.is_active_version = False
            superseded_record.superseded_by = record
            superseded_record.superseded_at = datetime.datetime.now()
            superseded_record.save()
            
            ReviewEvent.objects.create(
                emission_record=superseded_record,
                action_type='SUPERSEDED',
                notes=f"Superseded by batch {raw_record.batch.batch_version}"
            )
            
        raw_record.ingestion_status = 'PARSED'
        raw_record.save()
        
        ReviewEvent.objects.create(
            emission_record=record,
            action_type='AUTO_NORMALIZED',
            notes="Machine inferred normalization completed."
        )
