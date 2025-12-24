from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Avg, Count
from decimal import Decimal
from .models import ParkingRecord
from .serializers import ParkingRecordSerializer, VehicleSearchResponseSerializer

class VehicleSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        plate_number = request.query_params.get('plate_number', '').strip()
        
        # Validate plate number parameter
        if not plate_number:
            return Response(
                {'error': 'plate_number parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For regular users, search across all organizations
        # For organization admins, restrict to their organization
        if request.user.role == 'organization_admin' and request.user.organization:
            # Organization admin - filter by their organization
            vehicle_records = ParkingRecord.objects.filter(
                organization=request.user.organization.name,
                plate_number__icontains=plate_number
            ).order_by('-entry_time')
        else:
            # Regular users and super admins - search all organizations
            vehicle_records = ParkingRecord.objects.filter(
                plate_number__icontains=plate_number
            ).order_by('-entry_time')
        
        # Check if records exist
        if not vehicle_records.exists():
            return Response(
                {'error': 'No vehicle records found for the specified plate number'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Compute analytics
        analytics_data = vehicle_records.aggregate(
            total_visits=Count('id'),
            total_amount_paid=Sum('amount_paid'),
            average_payment=Avg('amount_paid')
        )
        
        # Visit count per location
        location_counts = vehicle_records.values('organization').annotate(
            count=Count('id')
        )
        visit_count_per_location = {
            item['organization']: item['count'] 
            for item in location_counts
        }
        
        # Handle None values
        analytics_data['total_amount_paid'] = analytics_data['total_amount_paid'] or Decimal('0.00')
        analytics_data['average_payment'] = analytics_data['average_payment'] or Decimal('0.00')
        analytics_data['visit_count_per_location'] = visit_count_per_location
        
        # Serialize data
        vehicle_serializer = ParkingRecordSerializer(vehicle_records, many=True)
        
        response_data = {
            'vehicle_records': vehicle_serializer.data,
            'analytics': analytics_data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)