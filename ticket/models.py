from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator 

# user model 
class User(AbstractUser):
    language = models.CharField(default='english', max_length=30)

    pass

# Ticket
class Ticket(models.Model):
    name = models.CharField(max_length=30)
    date = models.DateField()
    disease = models.CharField(max_length=300)
    insurance = models.BooleanField(default=True)
    indian = models.BooleanField(default=True)
    paid = models.BooleanField(default=False)
    confirm = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set the field to now when the object is first created.
    age = models.IntegerField(validators=[MinValueValidator(6), MaxValueValidator(122)], null=True)
    total_cost = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(1000)], null=True, blank=True)

    def total(self):
        # Ticket prices
        return 45
    
    def save(self, *args, **kwargs):
        self.total_cost = self.total()
        super().save(*args, **kwargs)
