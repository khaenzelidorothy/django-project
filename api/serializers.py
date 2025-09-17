from rest_framework import serializers
from django.conf import settings
from orders.models import Order, Rating, OrderTracking, CustomDesignRequest
from cart.models import ShoppingCart, CartItem
from products.models import Inventory
from .daraja import DarajaAPI
from payments.models import Payment
from users.models import User
from django.core.validators import validate_email, URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework.validators import UniqueValidator
from rest_framework.authtoken.models import Token
from users.models import User, ArtisanPortfolio, Profile
from users.utils import send_forgot_password_email

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'

    def validate_order_type(self, value):
        if value not in ['ready-made', 'custom']:
            raise serializers.ValidationError("Invalid order_type")
        return value

    def validate(self, value):
        status = value.get('status')
        payment_status = value.get('payment_status')
        order_type = value.get('order_type')

        if status == 'confirmed' and payment_status != 'completed':
            raise serializers.ValidationError(
                "Payment must be completed if order status is confirmed."
            )

        if status == 'rejected':
            if not value.get('rejected_reason') or not value.get('rejected_date'):
                raise serializers.ValidationError(
                    "Rejected orders must have reason and date."
                )

        return value


class RatingSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)

    class Meta:
        model = Rating
        fields = '__all__'
        read_only_fields = ['rating_id', 'created_at']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

class OrderTrackingSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)

    class Meta:
        model = OrderTracking
        fields = '__all__'
        read_only_fields = ['tracking_id', 'update_timestamp', 'created_at', 'approval_timestamp']

class CustomDesignRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomDesignRequest
        fields = '__all__'
        read_only_fields = ['request_id', 'created_at']


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'


class ShoppingCartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = ShoppingCart
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['id', 'paid_at', 'released_at', 'transaction_date']

class STKPushSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    buyer_phone = serializers.CharField(max_length=15)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    transaction_code = serializers.CharField(max_length=100)
    transaction_desc = serializers.CharField(max_length=255)

    def validate(self, data):
        order = Order.objects.get(id=data['order_id'])
        buyer = order.buyer_id
        artisan = order.artisan_id
        data['artisan_phone'] = artisan.phone_number
        if not data.get('buyer_phone'):
            data['buyer_phone'] = buyer.phone_number
        return data

class DeliveryConfirmSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()

class RefundSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=255)

class ArtisanPortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtisanPortfolio
        fields = ["portfolio_id", "title", "description", "created_at", "image_urls"]
        read_only_fields = ["portfolio_id", "created_at"]
    def validate(self, attrs):
        if not attrs.get("title"):
            raise serializers.ValidationError({"title": "Title is required for the portfolio."})
        if not attrs.get("description"):
            raise serializers.ValidationError({"description": "Description is required for the portfolio."})
        image_urls = attrs.get("image_urls", [])
        if not isinstance(image_urls, list) or len(image_urls) < 10:
            raise serializers.ValidationError({
                "image_urls": "At least 10 valid image URLs are required."
            })
        validator = URLValidator()
        for url in image_urls:
            try:
                validator(url)
            except DjangoValidationError:
                raise serializers.ValidationError({"image_urls": f"Invalid image URL: {url}"})
        return attrs

class UserRegistrationSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField(read_only=True)
    password = serializers.CharField(write_only=True, required=True)
    portfolio = ArtisanPortfolioSerializer(write_only=True, required=False)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    national_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="National ID already exists.")]
    )
    phone_number = serializers.CharField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="Phone number already exists.")]
    )
    class Meta:
        model = User
        fields = [
            "token", "email", "password", "first_name", "last_name",
            "user_type", "phone_number", "image_url",
            "latitude", "longitude", "national_id", "portfolio"
        ]
        read_only_fields = ["id", "token"]

    def get_token(self, obj):
        token, _ = Token.objects.get_or_create(user=obj)
        return token.key

    def validate_email(self, value):
        validate_email(value)
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_phone_number(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def validate(self, attrs):
        user_type = attrs.get("user_type")
        required_fields = ["email", "password", "first_name", "last_name", "phone_number", "user_type"]
        missing = [f for f in required_fields if not attrs.get(f)]
        if missing:
            raise serializers.ValidationError({f: "This field is required." for f in missing})
        if user_type == "ARTISAN":
            portfolio_data = attrs.get("portfolio")
            if not portfolio_data:
                raise serializers.ValidationError({
                    "portfolio": "Artisans must provide a portfolio with at least 10 valid image URLs."
                })
            if not attrs.get("national_id"):
                raise serializers.ValidationError({"national_id": "National ID is required for artisans."})
            if attrs.get("latitude") is None or attrs.get("longitude") is None:
                raise serializers.ValidationError({
                    "latitude": "Latitude is required for artisans.",
                    "longitude": "Longitude is required for artisans."
                })

            portfolio_serializer = ArtisanPortfolioSerializer(data=portfolio_data)
            portfolio_serializer.is_valid(raise_exception=True)
        else:
            attrs.pop("portfolio", None)
            attrs["national_id"] = None
            attrs["latitude"] = None
            attrs["longitude"] = None
        return attrs

    def create(self, validated_data):
        portfolio_data = validated_data.pop("portfolio", None)
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.is_active = False  
        user.save()
        if user.user_type == "ARTISAN" and portfolio_data:
            ArtisanPortfolio.objects.create(artisan=user, **portfolio_data)
        user.generate_otp()
        send_forgot_password_email(user.email, user.otp)
        return user

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    def validate(self, data):
        identifier = data.get("identifier")
        password = data.get("password")
        if not identifier or not password:
            raise serializers.ValidationError({"non_field_errors": "Must provide email/phone and password."})
        try:
            if "@" in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone_number=identifier)
        except User.DoesNotExist:
            raise serializers.ValidationError({"non_field_errors": "Invalid email/phone or password."})
        if not user.is_active or not user.check_password(password):
            raise serializers.ValidationError({"non_field_errors": "Invalid email/phone or password."})
        token, _ = Token.objects.get_or_create(user=user)
        data["user"] = user
        data["token"] = token.key
        return data


class CustomUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [ "email", "full_name", "phone_number", "image_url", "user_type"]
        read_only_fields = [ "email", "user_type"]
    def get_full_name(self, obj):
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip()

class ProfileSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    class Meta:
        model = Profile
        fields = ["id", "user", "image_url"]
        read_only_fields = ["id", "user"]

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        try:
            user.generate_otp()
            send_forgot_password_email(user.email, user.otp)
        except Exception as e:
            raise serializers.ValidationError(f"Failed to send OTP email: {str(e)}")
        return value

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    def validate(self, data):
        try:
            user = User.objects.get(email=data["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})
        if not user.otp or user.otp != data["otp"]:
            raise serializers.ValidationError({"otp": "Invalid OTP."})
        if not user.otp_exp or user.otp_exp < timezone.now():
            raise serializers.ValidationError({"otp": "OTP has expired."})
        user.otp_verified = True
        user.is_active = True  
        user.otp = None
        user.otp_exp = None
        user.save(update_fields=["otp_verified", "is_active", "otp", "otp_exp"])
        return data

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    def validate(self, data):
        try:
            user = User.objects.get(email=data["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})
        if user.is_active:
            raise serializers.ValidationError({"email": "This account is already verified."})
        user.generate_otp()
        send_forgot_password_email(user.email, user.otp)
        return {"message": "A new OTP has been sent to your email."}

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    def validate(self, data):
        if data.get("new_password") != data.get("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords must match."})
        try:
            user = User.objects.get(email=data["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})
        if not user.otp_verified:
            raise serializers.ValidationError({"email": "OTP not verified."})
        try:
            validate_password(data["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        return data
    def save(self, **kwargs):
        user = User.objects.get(email=self.validated_data["email"])
        user.set_password(self.validated_data["new_password"])
        user.otp = None
        user.otp_exp = None
        user.otp_verified = False
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'user_id', 'user_type', 'first_name', 'last_name', 'email', 'phone_number',
            'address', 'latitude', 'longitude',
        ]
        read_only_fields = ['latitude', 'longitude']


class NearbyArtisanSearchSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    radius = serializers.DecimalField(max_digits=5, decimal_places=2, default=50)
