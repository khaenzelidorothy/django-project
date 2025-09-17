from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    OrderViewSet, RatingViewSet,
    OrderTrackingViewSet, CustomDesignRequestViewSet,ShoppingCartViewSet, CartItemViewSet,InventoryViewSet,
    PaymentViewSet,
    daraja_callback,
    STKPushView,
    DeliveryConfirmView,
    RefundPaymentView,
    UserRegistrationView, LoginView, ForgotPasswordView,
    OTPVerificationView, PasswordResetView,
    AdminListUsersView, UserViewSet, ArtisanPortfolioViewSet, UserProfileView,
    NearbyArtisansView
)

artisan_portfolio_list = ArtisanPortfolioViewSet.as_view({'get': 'list', 'post': 'create'})
artisan_portfolio_detail = ArtisanPortfolioViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'ratings', RatingViewSet, basename='rating')
router.register(r'trackings', OrderTrackingViewSet, basename='ordertracking')
router.register(r'custom-requests', CustomDesignRequestViewSet, basename='customdesignrequest')
router.register(r'carts', ShoppingCartViewSet, basename='cart')
router.register(r'cart-items', CartItemViewSet, basename='cartitem')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'payment', PaymentViewSet, basename='payment')
router.register(r'users', UserViewSet)
router.register(r'portfolio', ArtisanPortfolioViewSet, basename='portfolio')

urlpatterns = [
    path('api/', include(router.urls)),
    path('daraja/stk-push/', STKPushView.as_view(), name='daraja-stk-push'),
    path('daraja/callback/', daraja_callback, name='daraja-callback'),
    path('delivery/confirm/', DeliveryConfirmView.as_view(), name='delivery-confirm'),
    path('payment/refund/', RefundPaymentView.as_view(), name='payment-refund'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-otp/', OTPVerificationView.as_view(), name='verify-otp'),
    path('reset-password/', PasswordResetView.as_view(), name='reset-password'),
    path('admin/users/', AdminListUsersView.as_view(), name='admin-list-users'),
    path('artisan-portfolio/', artisan_portfolio_list, name='artisan-portfolio-list'),
    path('profile/',UserProfileView.as_view(), name = 'user-profile'),
    path('api/nearby-artisans/', NearbyArtisansView.as_view(), name='nearby-artisans')
]












