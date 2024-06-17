from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Channel
import os
import binascii

BASE = 2
MODULUS = int("A4E02E7144D7189965AA9901013921BD721AE84072B4F41A3ED4AD3F5DC1C403", 16)

class ChannelTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.sender = User.objects.create_user(username='sender', password='password123')
        self.recipient = User.objects.create_user(username='recipient', password='password123')
        self.client.force_authenticate(user=self.sender)

    def test_create_channel(self):
        url = '/api/channels/'
        data = {
            'recipient_user': self.recipient.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Channel.objects.count(), 1)
        self.assertEqual(Channel.objects.get().sender_user, self.sender)
        self.assertEqual(Channel.objects.get().recipient_user, self.recipient)

    def test_accept_channel(self):
        channel = Channel.objects.create(sender_user=self.sender, recipient_user=self.recipient, name='channel1')
        self.client.force_authenticate(user=self.recipient)
        url = f'/api/channels/{channel.id}/accept/'
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        channel.refresh_from_db()
        self.assertTrue(channel.accepted)

    def test_secret_exchange(self):
        channel = Channel.objects.create(sender_user=self.sender, recipient_user=self.recipient, name='channel1', accepted=True)
        url = f'/api/secret_exchange/{channel.id}/'

        
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('secret_key', response.data)
        sender_secret_key = response.data['secret_key']
        channel.refresh_from_db()
        self.assertIsNotNone(channel.initial_sender_secret)

        
        self.client.force_authenticate(user=self.recipient)
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('secret_key', response.data)
        recipient_secret_key = response.data['secret_key']
        channel.refresh_from_db()
        self.assertIsNotNone(channel.initial_recipient_secret)

    def test_key_generation(self):
        channel = Channel.objects.create(sender_user=self.sender, recipient_user=self.recipient, name='channel1', accepted=True)
        sender_secret_key = int(binascii.hexlify(os.urandom(32)), 16)
        recipient_secret_key = int(binascii.hexlify(os.urandom(32)), 16)
        channel.initial_sender_secret = pow(BASE, sender_secret_key, MODULUS)
        channel.initial_recipient_secret = pow(BASE, recipient_secret_key, MODULUS)
        channel.save()

        
        self.client.force_authenticate(user=self.sender)
        url = f'/api/key_generation/{channel.id}/'
        response = self.client.post(url, {'secret_key': sender_secret_key}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('key', response.data)
        sender_key = response.data['key']

        
        self.client.force_authenticate(user=self.recipient)
        response = self.client.post(url, {'secret_key': recipient_secret_key}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('key', response.data)
        recipient_key = response.data['key']

       
        self.assertEqual(sender_key, recipient_key)
