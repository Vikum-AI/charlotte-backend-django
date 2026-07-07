"""
URL configuration for charlotte project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path

from api.core.utils.case_streams import case_graph_stream, case_status_stream

urlpatterns = [
    path('cases/<str:case_id>/events/graph', case_graph_stream),
    path('cases/<str:case_id>/events/graph/', case_graph_stream),
    path('cases/<str:case_id>/events/status', case_status_stream),
    path('cases/<str:case_id>/events/status/', case_status_stream),
    path('', include('api.core.urls')),
    path('', include('api.urls')),
    path('api/', include('api.core.urls')),
    path('api/', include('api.urls')),
]
