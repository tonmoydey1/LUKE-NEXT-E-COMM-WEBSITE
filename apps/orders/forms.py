from django import forms


class AddToCartForm(forms.Form):
    product_id = forms.IntegerField(widget=forms.HiddenInput)
    variant_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    quantity = forms.IntegerField(min_value=1, max_value=10, initial=1)


class CouponForm(forms.Form):
    code = forms.CharField(max_length=30)


class PincodeForm(forms.Form):
    pincode = forms.CharField(max_length=6, min_length=6)
