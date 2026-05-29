from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Address, Profile


class LuxeRegisterForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=80)
    last_name = forms.CharField(max_length=80, required=False)
    phone = forms.CharField(max_length=15)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "password1", "password2"]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another one.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already exists with this email. Please login instead.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            user.profile.phone = self.cleaned_data["phone"]
            user.profile.save(update_fields=["phone"])
        return user


class LuxeLoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or email")


class OTPForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6)


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=80)
    last_name = forms.CharField(max_length=80, required=False)
    email = forms.EmailField()

    class Meta:
        model = Profile
        fields = ["phone", "avatar"]


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["full_name", "phone", "line1", "line2", "city", "state", "pincode", "address_type", "is_default"]


class LuxePasswordResetForm(PasswordResetForm):
    pass


class LuxeSetPasswordForm(SetPasswordForm):
    pass
