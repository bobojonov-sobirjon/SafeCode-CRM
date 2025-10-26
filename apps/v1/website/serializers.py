from rest_framework import serializers
from apps.v1.website.models import Services, ServiceItems, Contacts


class ServiceItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceItems
        fields = ('id', 'service', 'content', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')
        

class ServicesSerializer(serializers.ModelSerializer):
    service_items = ServiceItemsSerializer(many=True, read_only=True)
    class Meta:
        model = Services
        fields = ('id', 'title', 'image', 'description', 'why_this_service', 'for_whom', 'price', 'created_at', 'updated_at', 'service_items')
        read_only_fields = ('created_at', 'updated_at')


class ContactsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contacts
        fields = ('id', 'address', 'phone', 'email', 'working_hours_mon_thu', 'working_hours_fri', 'working_hours_sat_sun', 'map_iframe', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')
        