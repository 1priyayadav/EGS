import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from emissions.models import EmissionRecord, ReviewEvent, Tenant, DataSource
from emissions.serializers import EmissionRecordSerializer, EmissionRecordUpdateSerializer
from emissions.services.ingestion import IngestionService

class EmissionRecordViewSet(viewsets.ModelViewSet):
    serializer_class = EmissionRecordSerializer
    
    def get_queryset(self):
        # We only want active versions for standard analyst views
        qs = EmissionRecord.objects.filter(is_active_version=True).prefetch_related('reviewevent_set', 'raw_record')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=False, methods=['GET'])
    def pending(self, request):
        qs = self.get_queryset().filter(status='PENDING', is_locked=False)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['GET'])
    def flagged(self, request):
        qs = self.get_queryset().filter(status='FLAGGED', is_locked=False)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['GET'])
    def stats(self, request):
        from django.db.models import Count
        status_counts = EmissionRecord.objects.filter(is_active_version=True).values('status').annotate(count=Count('id'))
        
        counts = { 'PENDING': 0, 'APPROVED': 0, 'REJECTED': 0, 'FLAGGED': 0 }
        for sc in status_counts:
            counts[sc['status']] = sc['count']
            
        total = sum(counts.values())
        counts['TOTAL'] = total
        
        return Response(counts)

    @action(detail=True, methods=['POST'])
    def review(self, request, pk=None):
        record = self.get_object()
        
        if record.is_locked:
            return Response({'error': 'Record is locked for audit.'}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = EmissionRecordUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        action_type = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        
        # Determine user (mocking authentication for prototype)
        user = request.user if request.user.is_authenticated else None
        
        if action_type == 'APPROVE':
            record.status = 'APPROVED'
            record.is_locked = True
            record.locked_at = datetime.datetime.now()
            record.reviewer = user
            record.save()
            
            ReviewEvent.objects.create(
                emission_record=record,
                action_type='APPROVED',
                changed_by=user,
                notes=notes
            )
            return Response({'status': 'approved'})
            
        elif action_type == 'REJECT':
            record.status = 'REJECTED'
            record.is_locked = True
            record.locked_at = datetime.datetime.now()
            record.reviewer = user
            record.save()
            
            ReviewEvent.objects.create(
                emission_record=record,
                action_type='REJECTED',
                changed_by=user,
                notes=notes
            )
            return Response({'status': 'rejected'})
            
        elif action_type == 'EDIT':
            corrected_payload = serializer.validated_data.get('corrected_payload')
            correction_reason = serializer.validated_data.get('correction_reason')
            
            if not corrected_payload or not correction_reason:
                return Response({'error': 'Corrected payload and reason required.'}, status=status.HTTP_400_BAD_REQUEST)
                
            before = record.analyst_corrected_payload or record.auto_normalized_payload
            
            record.analyst_corrected_payload = corrected_payload
            record.correction_reason = correction_reason
            # Reset status to pending so it can be approved after edit
            record.status = 'PENDING'
            record.validation_flags = []
            record.save()
            
            ReviewEvent.objects.create(
                emission_record=record,
                action_type='EDITED',
                changed_by=user,
                notes=notes or correction_reason,
                before_payload=before,
                after_payload=corrected_payload
            )
            return Response({'status': 'edited'})

class IngestionViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['POST'])
    def upload_json(self, request):
        # Extremely simplified for prototype
        tenant_id = request.data.get('tenant_id', 1)
        data_source_id = request.data.get('data_source_id', 1)
        payload = request.data.get('payload', [])
        
        tenant, _ = Tenant.objects.get_or_create(id=tenant_id, defaults={'name': 'Demo Tenant'})
        data_source, created = DataSource.objects.get_or_create(id=data_source_id, tenant=tenant, defaults={'name': 'Demo Source', 'source_type': 'TRAVEL'})
        
        if created:
            from emissions.models import SourceFieldMapping
            SourceFieldMapping.objects.bulk_create([
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='origin_airport', normalized_field='origin_airport'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='destination_airport', normalized_field='destination_airport'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='travel_type', normalized_field='activity_type'),
            ])
        
        batch = IngestionService.ingest_json(tenant, data_source, payload, uploader=None)
        return Response({'batch_id': batch.id, 'status': 'ingested'})

    @action(detail=False, methods=['POST'])
    def upload_csv(self, request):
        tenant_id = request.data.get('tenant_id', 1)
        data_source_id = request.data.get('data_source_id')
        file_obj = request.FILES.get('file')
        
        if not file_obj or not data_source_id:
            return Response({'error': 'File and data_source_id required'}, status=status.HTTP_400_BAD_REQUEST)
            
        tenant, _ = Tenant.objects.get_or_create(id=tenant_id, defaults={'name': 'Demo Tenant'})
        data_source_type = 'SAP' if str(data_source_id) == '1' else 'UTILITY'
        data_source, created = DataSource.objects.get_or_create(id=data_source_id, tenant=tenant, defaults={'name': 'Demo Source', 'source_type': data_source_type})
        
        if created and data_source_type == 'SAP':
            from emissions.models import SourceFieldMapping
            SourceFieldMapping.objects.bulk_create([
                # Native German SAP Headers
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='WERKS', normalized_field='plant_code'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='MENGE', normalized_field='raw_value', transform_type='float'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='MEINS', normalized_field='raw_unit'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='BUDAT', normalized_field='start_date'),
                # English Translated Headers (Fallback)
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='Plant_Code', normalized_field='plant_code'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='Quantity', normalized_field='raw_value', transform_type='float'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='Unit', normalized_field='raw_unit'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='Posting_Date', normalized_field='start_date'),
            ])
        elif created and data_source_type == 'UTILITY':
            from emissions.models import SourceFieldMapping
            SourceFieldMapping.objects.bulk_create([
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='Meter_ID', normalized_field='meter_id'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='Usage_kWh', normalized_field='raw_value', transform_type='float'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='Start_Date', normalized_field='start_date'),
                SourceFieldMapping(tenant=tenant, data_source=data_source, source_field='End_Date', normalized_field='end_date'),
            ])
            
        batch = IngestionService.ingest_csv(tenant, data_source, file_obj, uploader=None, file_name=file_obj.name)
        return Response({'batch_id': batch.id, 'status': 'ingested'})
