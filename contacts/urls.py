from django.urls import path
from . import views

urlpatterns = [
    path('', views.contact_page, name='contact'),
    # Commentaires
    path('api/comments/get/', views.GetCommentsView.as_view(), name='get_comments'),
    path('api/comments/create/', views.CreateCommentView.as_view(), name='create_comment'),
    path('api/comments/like/', views.LikeCommentView.as_view(), name='like_comment'),
    path('api/comments/report/', views.ReportCommentView.as_view(), name='report_comment'),
    
    # Témoignages
    path('testimonials/', views.TestimonialListView.as_view(), name='testimonials'),
    path('testimonials/<uuid:testimonial_id>/', views.TestimonialDetailView.as_view(), name='testimonial_detail'),
    path('testimonials/create/', views.TestimonialCreateView.as_view(), name='create_testimonial'),
    path('api/testimonials/', views.TestimonialAPIView.as_view(), name='api_testimonials'),
    path('api/testimonials/comment/', views.TestimonialCommentView.as_view(), name='testimonial_comment'),
    
    # Administration
    path('admin/comments/', views.AdminCommentsView.as_view(), name='admin_comments'),
    path('admin/testimonials/', views.AdminTestimonialsView.as_view(), name='admin_testimonials'),
    path('admin/comments/<uuid:comment_id>/approve/', views.ApproveCommentView.as_view(), name='approve_comment'),
    path('admin/comments/<uuid:comment_id>/reject/', views.RejectCommentView.as_view(), name='reject_comment'),
    path('admin/testimonials/<uuid:testimonial_id>/publish/', views.PublishTestimonialView.as_view(), name='publish_testimonial'),
]
