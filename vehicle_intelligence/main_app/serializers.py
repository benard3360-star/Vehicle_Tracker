from rest_framework import serializers
from .models import ParkingRecord

class ParkingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingRecord
        fields = [
            'id', 'plate_number', 'entry_time', 'exit_time', 
            'vehicle_type', 'vehicle_brand', 'amount_paid', 
            'payment_method', 'organization', 'parking_duration_minutes'
        ]

class VehicleAnalyticsSerializer(serializers.Serializer):
    total_visits = serializers.IntegerField()
    total_amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_payment = serializers.DecimalField(max_digits=10, decimal_places=2)
    visit_count_per_location = serializers.DictField()

class VehicleSearchResponseSerializer(serializers.Serializer):
    vehicle_records = ParkingRecordSerializer(many=True)
    analytics = VehicleAnalyticsSerializer()