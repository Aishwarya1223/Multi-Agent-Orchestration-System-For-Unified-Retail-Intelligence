from django.urls import path
from .consumers import QueryConsumer

websocket_urlpatterns = [
    path("ws/query/", QueryConsumer.as_asgi()),
]
