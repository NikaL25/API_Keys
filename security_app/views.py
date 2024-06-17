# views.py

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import Channel
from .serializers import ChannelSerializer
import random
import os
import binascii
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.core.exceptions import ObjectDoesNotExist


BASE = 2
MODULUS = int('A4E02E7144D7189965AA9901013921BD721AE84072B4F41A3ED4AD3F5DC1C403', 16)

class ChannelViewSet(ModelViewSet):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        recipient_user_id = self.request.data.get('recipient_user')
        if recipient_user_id:
            try:
                recipient_user = User.objects.get(pk=recipient_user_id)
                serializer.save(sender_user=self.request.user, recipient_user=recipient_user, name=self._generate_random_name())
            except User.DoesNotExist:
                raise ValidationError(f"User with id {recipient_user_id} does not exist.")
        else:
            raise ValidationError("Recipient user ID must be provided.")

    def get_queryset(self):
        user = self.request.user
        return Channel.objects.filter(sender_user=user) | Channel.objects.filter(recipient_user=user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        channel = self.get_object()
        if channel.recipient_user != request.user:
            raise ValidationError("You are not the recipient for this channel.")
        channel.accepted = True
        channel.save()
        return Response({"status": "Channel accepted"}, status=status.HTTP_200_OK)

    def _generate_random_name(self):
        return f'channel_{random.randint(1000, 9999)}'



from rest_framework.views import APIView

class SecretExchangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, channel_id):
        channel = Channel.objects.get(id=channel_id)
        if channel.sender_user != request.user and channel.recipient_user != request.user:
            raise ValidationError("You do not have access to this channel.")
        if not channel.accepted:
            return Response({"error": "Channel not accepted yet"}, status=status.HTTP_400_BAD_REQUEST)

        secret_key = int(binascii.hexlify(os.urandom(32)), 16)

        if channel.sender_user == request.user:
            sender_secret = pow(BASE, secret_key, MODULUS)
            channel.initial_sender_secret = sender_secret
        else:
            recipient_secret = pow(BASE, secret_key, MODULUS)
            channel.initial_recipient_secret = recipient_secret

        channel.save()
        return Response({"secret_key": secret_key}, status=status.HTTP_200_OK)


class KeyGenerationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, channel_id):
        channel = Channel.objects.get(id=channel_id)
        secret_key = request.data.get('secret_key')
        if not secret_key:
            return Response({"error": "secret_key is required"}, status=status.HTTP_400_BAD_REQUEST)

        secret_key = int(secret_key)

        if channel.sender_user == request.user:
            shared_key = pow(channel.initial_recipient_secret, secret_key, MODULUS)
        elif channel.recipient_user == request.user:
            shared_key = pow(channel.initial_sender_secret, secret_key, MODULUS)
        else:
            raise ValidationError("You do not have access to this channel.")

        return Response({"key": shared_key}, status=status.HTTP_200_OK)
