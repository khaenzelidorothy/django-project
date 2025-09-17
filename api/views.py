
from django.shortcuts import render
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from cart.models import ShoppingCart, CartItem
from .serializers import ShoppingCartSerializer, CartItemSerializer,InventorySerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from products.models import Inventory
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model 
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from payments.models import Payment
from orders.models import Order
from users.models import User
from django.utils import timezone
import datetime
from .daraja import DarajaAPI
from orders.models import Order, Rating, OrderTracking, CustomDesignRequest
import logging
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound
from users.models import User, ArtisanPortfolio
from users.models import Profile
import django_filters.rest_framework
from django_filters.rest_framework import DjangoFilterBackend
from users.permissions import AdminPermission, ArtisanPermission
from rest_framework.views import APIView
from django.db.models import F, FloatField
from .utils import haversine
from django.db.models.functions import ACos, Cos, Radians, Sin
from .serializers import (
    OrderSerializer, RatingSerializer,
    OrderTrackingSerializer, CustomDesignRequestSerializer,
    STKPushSerializer,
    PaymentSerializer,
    DeliveryConfirmSerializer,
    RefundSerializer,
    UserRegistrationSerializer,
    LoginSerializer,
    CustomUserSerializer,
    ForgotPasswordSerializer,
    OTPVerificationSerializer,
    PasswordResetSerializer,
    ProfileSerializer,
    ArtisanPortfolioSerializer,
    UserSerializer, NearbyArtisanSearchSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer 

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'buyer_orders'):  
            return Order.objects.filter(buyer_id=user)
        elif hasattr(user, 'artisan_orders'):
            return Order.objects.filter(artisan_id=user)
        return Order.objects.none()

    def confirm_payment(self, request, pk=None):
        order = self.get_object()
        if order.payment_status != 'pending':
            raise ValidationError("Payment is not pending.")
        if self.request.user.user_type != 'buyer':
            raise PermissionDenied("Only buyers can confirm payment.")
        order.payment_status = 'completed'
        order.status = 'confirmed'
        order.save()
        return Response({"message": "Payment confirmed", "payment_status": order.payment_status})

class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer


class OrderTrackingViewSet(viewsets.ModelViewSet):
    queryset = OrderTracking.objects.all()
    serializer_class = OrderTrackingSerializer


class CustomDesignRequestViewSet(viewsets.ModelViewSet):
    queryset = CustomDesignRequest.objects.all()
    serializer_class = CustomDesignRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'buyer_requests'):
            return CustomDesignRequest.objects.filter(buyer_id=user)
        elif hasattr(user, 'artisan_requests'):
            return CustomDesignRequest.objects.filter(artisan_id=user)
        return CustomDesignRequest.objects.none()
    
    def perform_create(self, serializer):
        if self.request.user.user_type != 'buyer':
            raise PermissionDenied("Only buyers can create custom design requests.")
        serializer.save(buyer_id=self.request.user)

    def accept_request(self, request, pk=None):
        custom_request = self.get_object()
        if self.request.user.user_type != 'artisan':
            raise PermissionDenied("Only artisans can accept custom design requests.")
        if custom_request.artisan_id != self.request.user:
            raise PermissionDenied("You are not assigned to this request.")
        if custom_request.status != 'pending':
            raise ValidationError("Request is not pending.")
        custom_request.status = 'accepted'
        custom_request.save()
        return Response({"message": "Custom design request accepted", "status": custom_request.status})



class ShoppingCartViewSet(viewsets.ModelViewSet):
    queryset = ShoppingCart.objects.all()
    serializer_class = ShoppingCartSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        carts = self.queryset
        serializer = self.get_serializer(carts, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = False
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        partial = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()

class CartItemViewSet(viewsets.ViewSet):

    def create(self, request):
        user = request.user
        if isinstance(user, str):
            user = User.objects.get(username=user)
        cart, _ = ShoppingCart.objects.get_or_create(user=user)
        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(cart=cart)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        user = request.user
        if isinstance(user, str):
            user = User.objects.get(username=user)
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=user)
        serializer = CartItemSerializer(cart_item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        user = request.user
        if isinstance(user, str):
            user = User.objects.get(username=user)
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=user)
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        artisan_id = self.request.query_params.get('artisan_id')
        if artisan_id:
            return self.queryset.filter(artisan_id=artisan_id)
        return self.queryset



class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

class STKPushView(APIView):
    def post(self, request):
        serializer = STKPushSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            daraja = DarajaAPI()
            try:
                response = daraja.stk_push(
                    buyer_phone=data["buyer_phone"],
                    amount=data["amount"],
                    transaction_id=data["transaction_code"],
                    transaction_desc=data["transaction_desc"],
                )
                checkout_request_id = response.get('CheckoutRequestID', None)
                if checkout_request_id:
                    order = Order.objects.get(id=data['order_id'])
                    artisan = order.artisan_id
                    Payment.objects.create(
                        order_id=order,
                        artisan_id=artisan,
                        amount=data['amount'],
                        transaction_code=data['transaction_code'],
                        buyer_phone=data['buyer_phone'],
                        artisan_phone=artisan.phone_number,
                        status='held'
                    )
                return Response(response, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def daraja_callback(request):
    callback_data = request.data
    try:
        stk_callback = callback_data['Body']['stkCallback']
        checkout_request_id = stk_callback['CheckoutRequestID']
        result_code = stk_callback['ResultCode']
        result_desc = stk_callback['ResultDesc']
        payment = Payment.objects.get(transaction_code=checkout_request_id)
        payment.result_description = result_desc
        if result_code == 0:
            payment.status = 'held'
            items = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            item_dict = {item['Name']: item['Value'] for item in items}
            payment.mpesa_receipt_number = item_dict.get('MpesaReceiptNumber')
            trans_date_str = str(item_dict.get('TransactionDate'))
            trans_date = datetime.datetime.strptime(trans_date_str, '%Y%m%d%H%M%S')
            payment.transaction_date = timezone.make_aware(trans_date, timezone.get_current_timezone())
            payment.amount = item_dict.get('Amount')
            payment.buyer_phone = item_dict.get('PhoneNumber')
            payment.paid_at = timezone.now()
        elif result_code == 1:
            payment.status = 'refunded'
        payment.save()
    except Payment.DoesNotExist:
        pass
    except Exception as e:
        pass
    return Response({"status": "callback processed"})

class DeliveryConfirmView(APIView):
    def post(self, request):
        serializer = DeliveryConfirmSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                order = Order.objects.get(id=data['order_id'])
                payment = Payment.objects.get(order_id=order)
                if order.delivery_confirmed:
                    return Response({"detail": "Already confirmed."}, status=400)
                order.delivery_confirmed = True
                order.status = 'completed'
                order.save()
                daraja = DarajaAPI()
                response = daraja.b2c_payment(
                    artisan_phone=payment.artisan_phone,
                    amount=payment.amount,
                    transaction_id=payment.transaction_code,
                    transaction_desc="Delivery confirmed"
                )
                payment.status = "released"
                payment.released_at = timezone.now()
                payment.held_by_platform = False
                payment.save()
                return Response({"detail": "Delivery confirmed and payout released.", "b2c_response": response})
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RefundPaymentView(APIView):
    def post(self, request):
        serializer = RefundSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            try:
                order = Order.objects.get(id=data['order_id'])
                payment = Payment.objects.get(order_id=order)
                payment.status = "refunded"
                payment.refunded_reason = data['reason']
                payment.held_by_platform = False
                payment.refund_at = timezone.now()
                payment.save()
                return Response({"detail": "Refund processed."})
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def auto_release_payments():
    now = timezone.now()
    payments = Payment.objects.filter(status="held")
    for payment in payments:
        order = payment.order_id
        if order.delivery_confirmed:
            continue
        if payment.paid_at and (now - payment.paid_at).total_seconds() > 86400:
            daraja = DarajaAPI()
            try:
                response = daraja.b2c_payment(
                    artisan_phone=payment.artisan_phone,
                    amount=payment.amount,
                    transaction_id=payment.transaction_code,
                    transaction_desc="Auto-release after 24hr"
                )
                payment.status = "released"
                payment.released_at = now
                payment.held_by_platform = False
                payment.save()
            except Exception:
                continue

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        return user


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return Profile.objects.get(user=self.request.user)
        except Profile.DoesNotExist:
            raise NotFound("Profile not found for this user")


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        logger.debug("Login request received")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get('user')
        if not user:
            logger.error("Authentication returned no user.")
            return Response({"error": "User authentication failed"}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        user_serializer = CustomUserSerializer(user, context={'request': request})
        logger.info("Login successful for user: %s", getattr(user, 'email', 'unknown'))
        return Response({"token": token.key, "user": user_serializer.data}, status=status.HTTP_200_OK)

class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"success": True, "message": "OTP sent to email."}, status=status.HTTP_200_OK)

class OTPVerificationView(generics.GenericAPIView):
    serializer_class = OTPVerificationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"success": True, "message": "OTP verified successfully."}, status=status.HTTP_200_OK)

class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "message": "Password reset successfully."}, status=status.HTTP_200_OK)


class AdminListUsersView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated, AdminPermission]
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['user_type'] 


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated, AdminPermission]


class ArtisanPortfolioViewSet(viewsets.ModelViewSet):
    queryset = ArtisanPortfolio.objects.all()
    serializer_class = ArtisanPortfolioSerializer
    permission_classes = [IsAuthenticated, ArtisanPermission]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ArtisanPortfolio.objects.none()
        if user.user_type == 'ADMIN':
            return ArtisanPortfolio.objects.all()
        return ArtisanPortfolio.objects.filter(artisan=user)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated or user.user_type != 'ARTISAN':
            raise serializers.ValidationError({"detail": "Only artisans can create portfolios."})
        serializer.save(artisan=user)

class NearbyArtisansView(APIView):
    
    def post(self, request):
        serializer = NearbyArtisanSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lat = serializer.validated_data['latitude']
        lon = serializer.validated_data['longitude']
        radius = float(serializer.validated_data.get('radius', 50))

        artisans = User.objects.filter(
            user_type='artisan',
            latitude__isnull=False,
            longitude__isnull=False,
        )
        results = []
        for artisan in artisans:
            dist = haversine(lat, lon, artisan.latitude, artisan.longitude)
            if dist <= radius:
                portfolios = ArtisanPortfolio.objects.filter(artisan_id=artisan.user_id)
                portfolio_data = [
                    {
                        "title": p.title,
                        "description": p.description,
                        "image_urls": p.image_urls
                    } for p in portfolios
                ]
                results.append({
                    "artisan_id": artisan.user_id,
                    "first_name": artisan.first_name,
                    "last_name": artisan.last_name,
                    "distance_km": round(dist, 2),
                    "latitude": artisan.latitude,
                    "longitude": artisan.longitude,
                    "portfolio": portfolio_data,
                })

        results = sorted(results, key=lambda x: x['distance_km'])
        return Response({"artisans": results})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
