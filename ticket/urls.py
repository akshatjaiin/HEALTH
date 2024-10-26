from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("about_museum", views.about_museum, name="about_museum"),
    path("ticket/<int:ticket_id>/", views.ticket, name="ticket"),
    path("makepaymentsuccess", views.makepaymentsuccess, name="makepaymentsuccess"),
    path("booked", views.booked, name="booked"),
    path("about", views.about, name="about"),
    path("soon", views.soon, name="soon"),
    path("thankyou_from_penguins", views.thankyou, name="thankyou"),
]
