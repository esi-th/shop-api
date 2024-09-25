from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from phonenumber_field.serializerfields import PhoneNumberField

from rest_framework import serializers


class UserCreateSerializer(DjoserUserCreateSerializer):
    class Meta(DjoserUserCreateSerializer.Meta):
        fields = ['id', 'username', 'password', 'email', ]


class UserSerializer(DjoserUserSerializer):
    class Meta(DjoserUserSerializer.Meta):
        fields = ['id', 'username', 'email', 'phone_number', 'first_name', 'last_name', ]


class SignUpSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()
    password = serializers.CharField(max_length=60)

    def validate(self, data):
        if len(data['password']) < 8:
            raise serializers.ValidationError({'message': 'password should be more than 8 chars.'})
        if len(data['phone_number']) < 11:
            raise serializers.ValidationError({'message': 'phone number should be 11 chars.'})
        return data
    

class LoginSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()
    password = serializers.CharField(max_length=60)

    def validate(self, data):
        if len(data['password']) < 8:
            raise serializers.ValidationError({'message': 'password should be more than 8 chars.'})
        if len(data['phone_number']) < 11:
            raise serializers.ValidationError({'message': 'phone number should be 11 chars.'})
        return data


class ObtainAccessTokenSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()
    token = serializers.CharField(max_length=4)

    def validate(self, data):
        if len(data['token']) < 4:
            raise serializers.ValidationError({'message': 'invalid token.'})
        if len(data['phone_number']) < 11:
            raise serializers.ValidationError({'message': 'phone number should be 11 chars.'})
        return data


class ForgetPasswordSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()

    def validate(self, data):
        if len(data['phone_number']) < 11:
            raise serializers.ValidationError({'message': 'phone number should be 11 chars.'})
        return data
    

class ForgetPasswordVerifySerializer(serializers.Serializer):
    phone_number = PhoneNumberField()
    token = serializers.CharField(max_length=4)

    def validate(self, data):
        if len(data['token']) < 4:
            raise serializers.ValidationError({'message': 'invalid token.'})
        if len(data['phone_number']) < 11:
            raise serializers.ValidationError({'message': 'phone number should be 11 chars.'})
        return data


class PasswordResetSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(max_length=60)

    def validate(self, data):
        if len(data['password']) < 8:
            raise serializers.ValidationError({'message': 'password should be more than 8 chars.'})
        return data
