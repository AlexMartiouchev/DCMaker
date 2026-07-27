from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class UserRegisterForm(UserCreationForm):
    """Django's registration form plus an email address.

    Email is collected (and kept unique) so playtesters can be contacted
    about their feedback and can recover an account later.
    """

    email = forms.EmailField(help_text="Used for account recovery only.")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email
