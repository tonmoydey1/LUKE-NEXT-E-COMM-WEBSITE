import shutil
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.catalog.models import Category, Product, ProductImage, ProductVariant


class Command(BaseCommand):
    help = "Import GreatKart local product/category images into LuxeNest with matching product names."

    ROOT = Path(r"C:\Users\Tonmoy Dey\Downloads\greatkart_resources\greatkart_resources\GreatKart-Images\GreatKart Images")
    CATEGORY_DIR = ROOT / "Category"
    PRODUCT_DIR = ROOT / "Products"

    CATEGORY_FILES = {
        "GreatKart Shirts": "shirts.jpg",
        "GreatKart Jackets": "jackets.jpg",
        "GreatKart T-Shirts": "tshirts.jpg",
        "GreatKart Jeans": "jeans.jpg",
        "GreatKart Shoes": "shoes.png",
    }

    PRODUCTS = [
        {
            "name": "US Polo Assn Brown Hooded Jacket",
            "brand": "US Polo Assn",
            "category": "GreatKart Jackets",
            "price": "3499",
            "mrp": "5499",
            "file": "US-Polo-Assn_Jacket.jpg",
            "sizes": ["M", "L", "XL"],
        },
        {
            "name": "Great Printed Navy T-Shirt",
            "brand": "GreatKart",
            "category": "GreatKart T-Shirts",
            "price": "799",
            "mrp": "1299",
            "file": "Great-Tshirt.jpg",
            "sizes": ["S", "M", "L", "XL"],
        },
        {
            "name": "Van Heusen Navy Round Neck T-Shirt",
            "brand": "Van Heusen",
            "category": "GreatKart T-Shirts",
            "price": "999",
            "mrp": "1599",
            "file": "image13.jpg",
            "sizes": ["M", "L", "XL"],
        },
        {
            "name": "Jordan True Flight Basketball Shoes",
            "brand": "Jordan",
            "category": "GreatKart Shoes",
            "price": "5999",
            "mrp": "8999",
            "file": "jordan-true-flight-basketball-shoes.jpg",
            "sizes": ["7", "8", "9", "10"],
        },
        {
            "name": "On Cloud Waterproof Running Shoes",
            "brand": "On",
            "category": "GreatKart Shoes",
            "price": "8499",
            "mrp": "11999",
            "file": "image1.jpg",
            "sizes": ["7", "8", "9", "10"],
        },
        {
            "name": "Puma Ferrari Drift Cat Shoes",
            "brand": "Puma Ferrari",
            "category": "GreatKart Shoes",
            "price": "4299",
            "mrp": "6999",
            "file": "Puma-Ferrari-Shoes.jpg",
            "sizes": ["7", "8", "9", "10"],
        },
        {
            "name": "ATX Blue Slim Fit Jeans",
            "brand": "ATX",
            "category": "GreatKart Jeans",
            "price": "1799",
            "mrp": "2899",
            "file": "ATX-Jeans.jpg",
            "sizes": ["30", "32", "34", "36"],
        },
        {
            "name": "Mavi Dark Wash Denim Jeans",
            "brand": "Mavi",
            "category": "GreatKart Jeans",
            "price": "2199",
            "mrp": "3299",
            "file": "Mavi_jeans.jpg",
            "sizes": ["30", "32", "34", "36"],
        },
        {
            "name": "Classic Blue Denim Jeans",
            "brand": "GreatKart",
            "category": "GreatKart Jeans",
            "price": "1499",
            "mrp": "2399",
            "file": "image2.jpg",
            "sizes": ["30", "32", "34", "36"],
        },
        {
            "name": "Wrangler Navy Printed Casual Shirt",
            "brand": "Wrangler",
            "category": "GreatKart Shirts",
            "price": "1299",
            "mrp": "1999",
            "file": "Wrangler-Shirt.jpg",
            "sizes": ["S", "M", "L", "XL"],
        },
        {
            "name": "Sky Blue Formal Shirt",
            "brand": "GreatKart",
            "category": "GreatKart Shirts",
            "price": "1199",
            "mrp": "1899",
            "file": "Blue-Shirt.jpg",
            "sizes": ["S", "M", "L", "XL"],
        },
    ]

    def handle(self, *args, **options):
        if not self.CATEGORY_DIR.exists() or not self.PRODUCT_DIR.exists():
            static_root = settings.BASE_DIR / "static" / "greatkart-assets"
            self.CATEGORY_DIR = static_root / "category"
            self.PRODUCT_DIR = static_root / "products"
        if not self.CATEGORY_DIR.exists() or not self.PRODUCT_DIR.exists():
            raise CommandError(f"GreatKart image folders not found under {self.ROOT} or static/greatkart-assets")

        self._copy_static_assets()
        categories = self._upsert_categories()
        for product in self.PRODUCTS:
            self._upsert_product(product, categories[product["category"]])
        self.stdout.write(self.style.SUCCESS(f"Imported {len(self.PRODUCTS)} GreatKart products with matching images."))

    def _copy_static_assets(self):
        target = settings.BASE_DIR / "static" / "greatkart-assets"
        for source_dir in [self.CATEGORY_DIR, self.PRODUCT_DIR]:
            folder = "category" if source_dir == self.CATEGORY_DIR else "products"
            target_dir = target / folder
            target_dir.mkdir(parents=True, exist_ok=True)
            for source in source_dir.iterdir():
                if source.is_file():
                    shutil.copy2(source, target_dir / source.name)

    def _upsert_categories(self):
        parent, _ = Category.objects.update_or_create(
            slug="greatkart-fashion",
            defaults={"name": "GreatKart Fashion", "is_featured": True, "external_image_url": ""},
        )
        categories = {}
        for name, filename in self.CATEGORY_FILES.items():
            category, _ = Category.objects.update_or_create(
                slug=slugify(name),
                defaults={"name": name, "parent": parent, "is_featured": True, "external_image_url": ""},
            )
            source = self.CATEGORY_DIR / filename
            target_dir = settings.MEDIA_ROOT / "categories" / "greatkart"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / filename
            shutil.copy2(source, target)
            category.image = f"categories/greatkart/{filename}"
            category.external_image_url = ""
            category.save(update_fields=["image", "external_image_url"])
            categories[name] = category
        return categories

    def _upsert_product(self, data, category):
        slug = f"greatkart-{slugify(data['name'])}"
        product, _ = Product.objects.update_or_create(
            slug=slug,
            defaults={
                "category": category,
                "name": data["name"],
                "brand": data["brand"],
                "description": (
                    f"{data['brand']} {data['name']} imported from the GreatKart local asset pack. "
                    "The catalog image is matched directly to this product for clean listing, cart, wishlist, and invoice display."
                ),
                "price": Decimal(data["price"]),
                "mrp": Decimal(data["mrp"]),
                "gst_rate": Decimal("18.00"),
                "stock": 42,
                "rating": Decimal("4.60"),
                "review_count": 86,
                "external_image_url": "",
                "is_featured": True,
                "is_trending": True,
                "is_active": True,
            },
        )
        ProductImage.objects.filter(product=product).delete()
        source = self.PRODUCT_DIR / data["file"]
        target_dir = settings.MEDIA_ROOT / "products" / "greatkart"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / data["file"]
        shutil.copy2(source, target)
        ProductImage.objects.create(
            product=product,
            image=f"products/greatkart/{data['file']}",
            alt_text=data["name"],
            is_primary=True,
        )
        ProductVariant.objects.filter(product=product).delete()
        for size in data["sizes"]:
            ProductVariant.objects.create(product=product, name="Size", value=size, stock=16)
