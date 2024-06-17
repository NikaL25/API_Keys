from rest_framework import serializers
from .models import Channel

class ChannelSerializer(serializers.ModelSerializer):
    sender_user = serializers.StringRelatedField()
    recipient_user = serializers.StringRelatedField()

    class Meta:
        model = Channel
        fields = ['id', 'name', 'sender_user', 'recipient_user', 'accepted']
