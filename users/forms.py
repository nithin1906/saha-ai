# users/forms.py
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django import forms

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    last_name = forms.CharField(max_length=150, required=True, help_text='Required.')
    email = forms.EmailField(max_length=254, required=True, help_text='Required.')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def save(self, commit=True):
        # First, run the default save method to create the user with a username and password
        user = super(SignUpForm, self).save(commit=False)
        
        # Now, add the extra information from the form
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        
        if commit:
            user.save()
            
        return user

class LoginForm(AuthenticationForm):
    pass