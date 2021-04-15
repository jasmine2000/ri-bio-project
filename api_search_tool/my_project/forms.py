from django import forms

class SearchForm(forms.Form):
    author = forms.CharField(label='author', max_length=100)
    institution = forms.CharField(label='institution', max_length=100)
    sponsor = forms.CharField(label='sponsor', max_length=100)
    keyword = forms.CharField(label='keyword', max_length=100)