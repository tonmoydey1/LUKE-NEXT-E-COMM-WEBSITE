from django import forms

from .models import Review


class ProductSearchForm(forms.Form):
    q = forms.CharField(required=False)
    min_price = forms.DecimalField(required=False, min_value=0)
    max_price = forms.DecimalField(required=False, min_value=0)
    rating = forms.DecimalField(required=False, min_value=0, max_value=5)
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ("popular", "Popularity"),
            ("newest", "Newest"),
            ("price_low", "Price low to high"),
            ("price_high", "Price high to low"),
            ("best_rated", "Best rated"),
        ],
    )


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "title", "comment"]
