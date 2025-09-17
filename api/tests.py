from django.test import TestCase
from rest_framework.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from decimal import Decimal
from datetime import datetime, timedelta
from users.models import User, ArtisanPortfolio
from products.models import Inventory
from django.utils import timezone
from users.models import User
from orders.models import Order
from payments.models import Payment
from orders.models import (
    Order, Rating, OrderTracking, CustomDesignRequest
)
from api.serializers import (
    OrderSerializer, RatingSerializer,
    OrderTrackingSerializer, CustomDesignRequestSerializer
)
from api.views import(
    CustomDesignRequestViewSet, OrderTrackingViewSet,RatingViewSet, OrderViewSet
)
from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from users.models import ArtisanPortfolio

User = get_user_model()

class OrdersSerializersModelsTestCase(TestCase):
    def setUp(self):
        self.buyer = User.objects.create(
            user_type=User.BUYER,
            first_name="Dorothy",
            last_name="Khaenzeli",
            email="dorothy@example.com",
            phone_number="0712345678",
            national_id="1234567890"
        )
        self.artisan = User.objects.create(
            user_type=User.ARTISAN,
            first_name="Maxwell",
            last_name="David",
            email="maxwell@example.com",
            phone_number="0798765432",
            national_id="0987654321"
        )

        self.portfolio = ArtisanPortfolio.objects.create(
            artisan_id=self.artisan,
            title="Elegant Jewelry",
            description="Handcrafted jewelry pieces.",
            image_urls=["http://example.com/img1.jpg", "http://example.com/img2.jpg"]
        )


        self.order = Order.objects.create(
            buyer_id=self.buyer,
            artisan_id=self.artisan,
            order_type='ready-made',
            status='pending',
            quantity=1,
            total_amount=Decimal("100.00"),
            payment_status='pending'
        )

        self.custom_design_request = CustomDesignRequest.objects.create(
            buyer_id=self.buyer,
            artisan_id=self.artisan,
            description="Sample design",
            deadline=datetime.now().date() + timedelta(days=5),
            status='material-sourcing',
            quote_amount=Decimal("200.00"),
            material_price=Decimal("50.00"),
            labour_price=Decimal("50.00")
        )

        self.order_tracking = OrderTracking.objects.create(
            order_id=self.order,
            artisan_id=self.artisan,
            status='pending'
        )

        self.rating = Rating.objects.create(
            order_id=self.order,
            buyer_id=self.buyer,
            rating=5
        )
 
    def test_user_str_representation(self):
        self.assertEqual(str(self.buyer), "Dorothy Khaenzeli (dorothy@example.com)")
        self.assertEqual(str(self.artisan), "Maxwell David (maxwell@example.com)")

    def test_artisan_portfolio_str_representation(self):
        self.assertEqual(str(self.portfolio), "Elegant Jewelry")
        self.assertEqual(self.portfolio.artisan_id.user_type, User.ARTISAN)
        self.assertIsInstance(self.portfolio.image_urls, list)

    def test_user_email_unique_constraint(self):
        with self.assertRaises(Exception):
            User.objects.create(
                user_type=User.BUYER,
                first_name="Chebet",
                last_name="Uzed",
                email="dorothy@example.com",  
                phone_number="0799999999",
                national_id="1111111111"
            )

    def test_order_serializer_valid_order_type(self):
        serializer = OrderSerializer(instance=self.order)
        data = serializer.data
        self.assertIn(data['order_type'], ['ready-made', 'custom'])

    def test_order_serializer_invalid_order_type(self):
        data = {
            "buyer_id": self.buyer.user_id,
            "artisan_id": self.artisan.user_id,
            "order_type": 'invalid-type',
            "status": 'pending',
            "quantity": 1,
            "total_amount": "100.00",
            "payment_status": "pending"
        }
        serializer = OrderSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("order_type", serializer.errors)


    def test_order_serializer_confirmed_requires_payment_completed(self):
        data = {
            "buyer_id": self.buyer.user_id,
            "artisan_id": self.artisan.user_id,
            "order_type": 'ready-made',
            "status": 'confirmed',
            "quantity": 1,
            "total_amount": "100.00",
            "payment_status": "pending"
        }
        serializer = OrderSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        errors = serializer.errors
        self.assertTrue(
            'non_field_errors' in errors or
            'status' in errors or
            any('payment' in str(err).lower() for err in errors.values())
        )

    def test_rating_serializer_valid_rating(self):
        serializer = RatingSerializer(instance=self.rating)
        data = serializer.data
        self.assertTrue(1 <= data['rating'] <= 5)

    def test_rating_serializer_invalid_rating(self):
        data = {
            "order_id": self.order.id,
            "buyer_id": self.buyer.user_id,
            "rating": 6,
            "review_text": ""
        }
        serializer = RatingSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("rating", serializer.errors)

    def test_order_tracking_serializer_fields(self):
        serializer = OrderTrackingSerializer(instance=self.order_tracking)
        data = serializer.data
        self.assertIn('created_at', data)

    def test_custom_design_request_serializer_fields(self):
        serializer = CustomDesignRequestSerializer(instance=self.custom_design_request)
        data = serializer.data
        self.assertIn('created_at', data)


    def test_confirm_payment_only_buyer_can_confirm(self):
        self.order.payment_status = 'pending'
        self.order.status = 'pending'
        self.order.save()
        view = OrderViewSet()
        view.request = type("Request", (), {})()
        view.request.user = self.buyer
        view.kwargs = {'pk': self.order.pk}
        view.get_object = lambda: self.order
        response = view.confirm_payment(view.request, pk=self.order.pk)
        self.assertEqual(response.data['payment_status'], 'completed')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')
        self.assertEqual(self.order.payment_status, 'completed')

    def test_custom_design_request_only_buyer_can_create(self):
        view = CustomDesignRequestViewSet()
        view.request = type("Request", (), {})()
        view.request.user = self.artisan
        serializer = CustomDesignRequestSerializer(instance=self.custom_design_request)
        with self.assertRaises(PermissionDenied):
            view.perform_create(serializer)

    def test_accept_custom_design_request_only_artisan_can_accept(self):
        self.custom_design_request.status = 'pending'
        self.custom_design_request.artisan_id = self.artisan
        self.custom_design_request.save()
        view = CustomDesignRequestViewSet()
        view.request = type("Request", (), {})()
        view.request.user = self.buyer
        view.kwargs = {'pk': self.custom_design_request.pk}
        view.get_object = lambda: self.custom_design_request
        with self.assertRaises(PermissionDenied):
            view.accept_request(view.request, pk=self.custom_design_request.pk)

    def test_accept_custom_design_request_artisan_accepts(self):
        self.custom_design_request.status = 'pending'
        self.custom_design_request.artisan_id = self.artisan
        self.custom_design_request.save()
        view = CustomDesignRequestViewSet()
        view.request = type("Request", (), {})()
        view.request.user = self.artisan
        view.kwargs = {'pk': self.custom_design_request.pk}
        view.get_object = lambda: self.custom_design_request



class PaymentModelTest(TestCase):
    def setUp(self):
        self.buyer = User.objects.create(
            user_type='buyer',
            first_name='Buyer',
            last_name='Test',
            email='buyer@test.com',
            phone_number='0712345678',
            national_id='12345678'
        )
        self.artisan = User.objects.create(
            user_type='artisan',
            first_name='Artisan',
            last_name='Test',
            email='artisan@test.com',
            phone_number='0798765432',
            national_id='87654321'
        )
        self.order = Order.objects.create(
            buyer_id=self.buyer,
            artisan_id=self.artisan,
            quantity=1,
            total_amount=500.00,
            order_type='custom',
            status='pending'
        )

    def test_create_held_payment(self):
        payment = Payment.objects.create(
            order_id=self.order,
            artisan_id=self.artisan,
            amount=500.00,
            transaction_code='TX12345',
            status='held',
            buyer_phone=self.buyer.phone_number,
            artisan_phone=self.artisan.phone_number,
            paid_at=timezone.now()
        )
        self.assertEqual(payment.status, 'held')
        self.assertTrue(payment.held_by_platform)
        self.assertEqual(payment.amount, 500.00)
        self.assertEqual(payment.buyer_phone, '0712345678')
        self.assertEqual(payment.artisan_phone, '0798765432')

    def test_release_payment(self):
        payment = Payment.objects.create(
            order_id=self.order,
            artisan_id=self.artisan,
            amount=500.00,
            transaction_code='TX12345',
            status='held',
            buyer_phone=self.buyer.phone_number,
            artisan_phone=self.artisan.phone_number,
            paid_at=timezone.now()
        )
        payment.status = 'released'
        payment.released_at = timezone.now()
        payment.held_by_platform = False
        payment.save()
        self.assertEqual(payment.status, 'released')
        self.assertFalse(payment.held_by_platform)
        self.assertIsNotNone(payment.released_at)

    def test_refund_payment(self):
        payment = Payment.objects.create(
            order_id=self.order,
            artisan_id=self.artisan,
            amount=500.00,
            transaction_code='TX12345',
            status='held',
            buyer_phone=self.buyer.phone_number,
            artisan_phone=self.artisan.phone_number,
            paid_at=timezone.now()
        )
        payment.status = 'refunded'
        payment.refunded_reason = 'Buyer rejected product'
        payment.held_by_platform = False
        payment.save()
        self.assertEqual(payment.status, 'refunded')
        self.assertEqual(payment.refunded_reason, 'Buyer rejected product')
        self.assertFalse(payment.held_by_platform)


class AuthTests(APITestCase):
    def setUp(self):
        self.register_url = "/api/register/"
        self.login_url = "/api/login/"
        self.portfolio_url = "/api/portfolio/"

    @patch("api.serializers.send_forgot_password_email")  
    def test_register_user_success(self, mock_send_email):
        data = {
            "first_name": "John",
            "last_name": "Kinyanjui",
            "email": "john@example.com",
            "phone_number": "0712345678",
            "password": "password123",
            "user_type": "ARTISAN",
            "national_id": "12345678",
            "latitude": 1.2921,
            "longitude": 36.8219,
            "portfolio": {
                "title": "My Portfolio",
                "description": "Some description about portfolio",
                "image_urls": [f"http://example.com/img{i}.jpg" for i in range(10)],
            },
        }
        response = self.client.post(self.register_url, data, format="json")
        print("Register response data:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="john@example.com").exists())
        mock_send_email.assert_called_once()

    def test_register_missing_required_fields(self):
        data = {
            "first_name": "Jane",
            "password": "pass123",
            "user_type": "BUYER",
            "phone_number": "0712345678",
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_invalid_email_format(self):
        data = {
            "email": "not-an-email",
            "password": "pass123",
            "first_name": "Jane",
            "last_name": "Doe",
            "user_type": "BUYER",
            "phone_number": "0712345678",
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_invalid_phone_number_letters(self):
        data = {
            "email": "jane@example.com",
            "password": "pass123",
            "first_name": "Jane",
            "last_name": "Doe",
            "user_type": "BUYER",
            "phone_number": "07ab345678",
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_register_artisan_missing_portfolio(self):
        data = {
            "email": "jane@example.com",
            "password": "saltedpass",
            "first_name": "Jane",
            "last_name": "Doe",
            "user_type": "ARTISAN",
            "phone_number": "0712345679",
            "national_id": "987654321",
            "latitude": 1.1,
            "longitude": 36.8,
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("portfolio", response.data)


class PortfolioTests(APITestCase):
    def setUp(self):
        self.portfolio_url = "/api/portfolio/"
        self.artisan = User.objects.create_user(
            email="artisan@example.com",
            phone_number="0733333333",
            password="artisanpass",
            user_type="ARTISAN",
        )
        self.buyer = User.objects.create_user(
            email="buyer@example.com",
            phone_number="0744444444",
            password="buyerpass",
            user_type="BUYER",
        )
        self.admin = User.objects.create_superuser(email="admin@example.com", password="adminpass")
        self.admin.user_type = "ADMIN"
        self.admin.save()
        Token.objects.create(user=self.admin)

    def authenticate(self, user, password):
        response = self.client.post(
            "/api/login/", {"identifier": user.email, "password": password}, format="json"
        )
        token = response.data.get("token")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    def test_artisan_can_create_portfolio(self):
        self.authenticate(self.artisan, "artisanpass")
        data = {
            "title": "Test Portfolio",
            "description": "A test description",
            "image_urls": [f"http://example.com/img{i}.jpg" for i in range(10)],
        }
        response = self.client.post(self.portfolio_url, data, format="json")
        print("Create portfolio response data:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_portfolio_create_with_invalid_image_urls(self):
        self.authenticate(self.artisan, "artisanpass")
        data = {
            "title": "Some Portfolio",
            "description": "Testing invalid image URLs",
            "image_urls": [
                "http://valid-url.com/img.jpg",
                "invalid-url",
            ],
        }
        response = self.client.post(self.portfolio_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image_urls", response.data)

    def test_artisan_cannot_create_portfolio_with_less_than_10_images(self):
        self.authenticate(self.artisan, "artisanpass")
        data = {
            "title": "Incomplete Portfolio",
            "description": "Not enough images",
            "image_urls": ["http://example.com/img1.jpg"],
        }
        response = self.client.post(self.portfolio_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_buyer_cannot_create_portfolio(self):
        self.authenticate(self.buyer, "buyerpass")
        data = {
            "title": "Buyer Portfolio",
            "description": "Buyers cannot create portfolios",
            "image_urls": [f"http://example.com/img{i}.jpg" for i in range(10)],
        }
        response = self.client.post(self.portfolio_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_all_portfolios(self):
        self.authenticate(self.admin, "adminpass")
        ArtisanPortfolio.objects.create(
            artisan=self.artisan,
            title="Admin View Portfolio",
            description="Portfolio created for admin view test",
            image_urls=[f"http://example.com/img{i}.jpg" for i in range(10)],
        )
        response = self.client.get(self.portfolio_url, format="json")
        print("Admin view portfolios response data:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_buyer_can_view_portfolios_but_not_edit(self):
        self.authenticate(self.buyer, "buyerpass")
        response = self.client.get(self.portfolio_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data_edit = {
            "title": "Trying to edit",
            "description": "Change description",
            "image_urls": [f"http://example.com/img{i}.jpg" for i in range(10)],
        }
        response_post = self.client.post(self.portfolio_url, data_edit, format="json")
        self.assertEqual(response_post.status_code, status.HTTP_403_FORBIDDEN)
