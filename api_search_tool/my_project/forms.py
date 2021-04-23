from django import forms

class SearchForm(forms.Form):
    author = forms.CharField(label='author', max_length=100, required=False)
    institution = forms.CharField(label='institution', max_length=100, required=False)
    sponsor = forms.CharField(label='sponsor', max_length=100, required=False)
    city = forms.CharField(label='city', max_length=100, required=False)
    state = forms.CharField(label='state', max_length=100, required=False)
    keyword = forms.CharField(label='keyword', max_length=100, required=False)