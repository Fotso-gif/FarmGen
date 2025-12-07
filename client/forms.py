from django import forms
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import NewsletterSubscriber

class NewsletterSubscriptionForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre adresse email',
            'required': True
        }),
        label="Email"
    )
    
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Validation de l'email
        try:
            validate_email(email)
        except ValidationError:
            raise forms.ValidationError("Veuillez entrer une adresse email valide.")
        
        # Vérifier si l'email est déjà inscrit
        if NewsletterSubscriber.objects.filter(email=email, status='active').exists():
            raise forms.ValidationError("Cette adresse email est déjà inscrite à notre newsletter.")
        
        return email.lower()  # Normaliser l'email en minuscules