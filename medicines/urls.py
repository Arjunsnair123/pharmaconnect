from django.urls import path
from .views import MedicineSearchView, SubstituteSuggestionView,SmartSubstituteView,MedicineSuggestView

urlpatterns = [
    path('search/', MedicineSearchView.as_view()),
    path('substitutes/', SubstituteSuggestionView.as_view()),
    path('smart-substitutes/', SmartSubstituteView.as_view()), path("suggest/", MedicineSuggestView.as_view(), name="medicine_suggest"),

]