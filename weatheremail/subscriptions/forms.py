from django import forms

from subscriptions import models

# Create a list of first 100 tuple(city.id, str(city)
# city.id will be used to query DB
# str(city) is shown to the user
cities = models.City.objects.only(
    'id',
    'name',
    'state').order_by('population').reverse()[:100]
cities = [(city.id, str(city)) for city in cities]


# TODO: use some email validation tool like mailgun or other to only save
#       valid email in the DB.
#       City should be valid, since we provide the list.
#       Unless it's an AJAX call?
class SubscriptionForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'tabindex': '2', 'placeholder': 'Your Email', 'autocomplete': 'on'}))
    city = forms.ChoiceField(cities, widget=forms.Select(attrs={
        'id': 'subject', 'name': 'subject', 'tabindex': '4'}))
