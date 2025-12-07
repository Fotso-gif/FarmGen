from django import forms
from django.core.exceptions import ValidationError
from .models import Comment, Testimonial, CommentReport
import bleach

class CommentForm(forms.ModelForm):
    """Formulaire pour les commentaires"""
    
    class Meta:
        model = Comment
        fields = ['content', 'article']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Votre commentaire...',
                'maxlength': '2000'
            }),
            'article': forms.HiddenInput(),
        }
    
    def clean_content(self):
        """Nettoyer et valider le contenu"""
        content = self.cleaned_data.get('content', '').strip()
        
        # Vérifier la longueur
        if len(content) < 10:
            raise ValidationError("Le commentaire doit contenir au moins 10 caractères.")
        
        if len(content) > 2000:
            raise ValidationError("Le commentaire ne peut pas dépasser 2000 caractères.")
        
        # Nettoyer le HTML
        allowed_tags = ['b', 'i', 'u', 'strong', 'em', 'br', 'p']
        cleaned_content = bleach.clean(
            content,
            tags=allowed_tags,
            strip=True
        )
        
        return cleaned_content


class ReplyForm(CommentForm):
    """Formulaire pour les réponses aux commentaires"""
    
    class Meta(CommentForm.Meta):
        fields = ['content', 'parent']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Votre réponse...',
                'maxlength': '1000'
            }),
            'parent': forms.HiddenInput(),
        }


class TestimonialForm(forms.ModelForm):
    """Formulaire pour les témoignages"""
    
    agree_terms = forms.BooleanField(
        required=True,
        label="J'accepte les conditions d'utilisation et la politique de confidentialité"
    )
    
    class Meta:
        model = Testimonial
        fields = [
            'title', 'content', 'author_name', 'author_role',
            'author_company', 'author_location', 'rating',
            'author_photo', 'category', 'agree_terms'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de votre témoignage'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Votre témoignage...'
            }),
            'author_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre nom'
            }),
            'author_role': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre rôle/profession'
            }),
            'author_company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre entreprise/organisation'
            }),
            'author_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre localisation'
            }),
            'rating': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[(i, f'{i} étoile{"s" if i > 1 else ""}') for i in range(1, 6)]),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def clean_content(self):
        """Nettoyer et valider le contenu"""
        content = self.cleaned_data.get('content', '').strip()
        
        if len(content) < 50:
            raise ValidationError("Le témoignage doit contenir au moins 50 caractères.")
        
        if len(content) > 1000:
            raise ValidationError("Le témoignage ne peut pas dépasser 1000 caractères.")
        
        return content
    
    def clean_author_name(self):
        """Valider le nom de l'auteur"""
        name = self.cleaned_data.get('author_name', '').strip()
        
        if len(name) < 2:
            raise ValidationError("Le nom doit contenir au moins 2 caractères.")
        
        return name


class TestimonialCommentForm(CommentForm):
    """Formulaire pour les commentaires sur les témoignages"""
    
    class Meta(CommentForm.Meta):
        fields = ['content', 'testimonial']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Votre commentaire sur ce témoignage...',
                'maxlength': '1000'
            }),
            'testimonial': forms.HiddenInput(),
        }


class CommentReportForm(forms.ModelForm):
    """Formulaire pour signaler un commentaire"""
    
    class Meta:
        model = CommentReport
        fields = ['reason', 'description']
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Détaillez la raison de votre signalement...'
            }),
        }