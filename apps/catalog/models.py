from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="children", blank=True, null=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    external_image_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def hero_image(self):
        if self.external_image_url:
            return self.external_image_url
        return self.image.url if self.image else "/static/img/product-placeholder.svg"


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    mrp = models.DecimalField(max_digits=12, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    stock = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    external_image_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["is_active", "is_featured"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def discount_percent(self):
        if self.mrp and self.mrp > self.price:
            return round(((self.mrp - self.price) / self.mrp) * 100)
        return 0

    @property
    def hero_image(self):
        if self.external_image_url:
            return self.external_image_url
        image = self.images.filter(is_primary=True).first() or self.images.first()
        return image.image.url if image and image.image else "/static/img/product-placeholder.svg"

    def get_absolute_url(self):
        return reverse("catalog:product_detail", args=[self.slug])

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=160, blank=True)
    is_primary = models.BooleanField(default=False)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=80)
    value = models.CharField(max_length=80)
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product} - {self.name}: {self.value}"


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=180)
    discount_percent = models.PositiveIntegerField(default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    def __str__(self):
        return self.code


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(default=5)
    title = models.CharField(max_length=120)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["product", "user"]
        ordering = ["-created_at"]


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "product"]
