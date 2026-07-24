from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('analytics/', views.analytics, name='analytics'),
    path('profile/', views.profile, name='profile'),
    path('profile/export/polls/csv/', views.profile_export_polls_csv, name='profile_export_polls_csv'),
    path('profile/export/polls/json/', views.profile_export_polls_json, name='profile_export_polls_json'),
    path('profile/export/votes/csv/', views.profile_export_votes_csv, name='profile_export_votes_csv'),
    path('profile/export/votes/json/', views.profile_export_votes_json, name='profile_export_votes_json'),
    path('search/', views.search, name='search'),

    path('polls/', views.poll_list, name='poll_list'),
    path('polls/create/', views.poll_create, name='poll_create'),
    path('polls/<int:pk>/', views.poll_detail, name='poll_detail'),
    path('polls/<int:pk>/edit/', views.poll_edit, name='poll_edit'),
    path('polls/<int:pk>/manage/', views.poll_manage, name='poll_manage'),
    path('polls/<int:pk>/delete/', views.poll_delete, name='poll_delete'),
    path('polls/<int:pk>/toggle/', views.poll_toggle_active, name='poll_toggle_active'),
    path('polls/<int:pk>/vote/', views.poll_vote, name='poll_vote'),
    path('polls/<int:pk>/results/', views.poll_results, name='poll_results'),
    path('polls/<int:pk>/export/csv/', views.poll_export_csv, name='poll_export_csv'),
    path('polls/<int:pk>/export/json/', views.poll_export_json, name='poll_export_json'),
    path('polls/<int:pk>/questions/add/', views.question_create, name='question_create'),
    path('polls/<int:pk>/questions/<int:question_pk>/delete/', views.question_delete, name='question_delete'),
]
