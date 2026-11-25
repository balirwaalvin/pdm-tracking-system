from django.urls import path

from . import views

app_name = "feedback"

urlpatterns = [
    path("", views.ComplaintListView.as_view(), name="complaint_list"),
    path("new/", views.ComplaintCreateView.as_view(), name="complaint_create"),
    path("<int:pk>/", views.ComplaintDetailView.as_view(), name="complaint_detail"),
    path("<int:pk>/respond/", views.respond_to_complaint, name="complaint_respond"),
    path("appeals/", views.AppealListView.as_view(), name="appeal_list"),
    path("appeals/new/<int:loan_pk>/", views.file_appeal, name="appeal_create"),
    path("appeals/<int:pk>/", views.AppealDetailView.as_view(), name="appeal_detail"),
    path("appeals/<int:pk>/decide/", views.decide_appeal, name="appeal_decide"),
    path("stories/", views.StoryListView.as_view(), name="story_list"),
    path("stories/new/", views.StoryCreateView.as_view(), name="story_create"),
    path("stories/<int:pk>/", views.StoryDetailView.as_view(), name="story_detail"),
    path("stories/<int:pk>/edit/", views.StoryUpdateView.as_view(), name="story_edit"),
    path("stories/<int:pk>/submit/", views.submit_story, name="story_submit"),
    path("stories/<int:pk>/check/", views.check_story, name="story_check"),
]
