from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.csrf, name="csrf"),
    path("auth/register/", views.register, name="register"),
    path("auth/login/", views.login_view, name="login"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("auth/me/", views.me, name="me"),
    path("frames/", views.frames, name="frames"),
    path("modules/", views.modules, name="modules"),
    path("evaluate/", views.evaluate, name="evaluate"),
    path("simulate/", views.simulate, name="simulate"),
    path("designs/", views.designs, name="designs"),
    path("designs/<int:design_id>/", views.design_detail, name="design-detail"),
    path("gallery/", views.gallery, name="gallery"),
    path("shared/<str:share_slug>/", views.shared, name="shared"),
]
