from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FileViewSet, get_storage_savings

router = DefaultRouter()
router.register(r'files', FileViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path("savings/", get_storage_savings, name="get-storage-savings"),

]
