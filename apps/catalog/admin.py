from django.contrib import admin

from .models import Category, Coupon, Product, ProductImage, ProductVariant, Review, Wishlist


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "mrp", "stock", "rating", "is_featured", "is_trending", "is_active"]
    list_filter = ["category", "is_featured", "is_trending", "is_active"]
    search_fields = ["name", "brand", "description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "is_featured"]
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(Coupon)
admin.site.register(Review)
admin.site.register(Wishlist)
