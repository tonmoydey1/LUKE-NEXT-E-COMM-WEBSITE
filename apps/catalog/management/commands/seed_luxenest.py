from decimal import Decimal
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
import requests

from apps.catalog.models import Category, Coupon, Product, ProductImage, ProductVariant


class Command(BaseCommand):
    help = "Seed LuxeNest with demo categories, products, variants, and a coupon."

    CATEGORY_IMAGES = {
        "Electronics": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Schenker_VIA14_Laptop_asv2021-01.jpg/960px-Schenker_VIA14_Laptop_asv2021-01.jpg",
        "Luxury Fashion": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Sari_2.jpg/960px-Sari_2.jpg",
        "Home Living": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/EFTA00000289_-_Cozy_living_room_with_cream-colored_furniture_a_yellow_carpet_and_white_walls_featuring_a_sofa_armchair_floor_lamp_and_book_stack.jpg/960px-EFTA00000289_-_Cozy_living_room_with_cream-colored_furniture_a_yellow_carpet_and_white_walls_featuring_a_sofa_armchair_floor_lamp_and_book_stack.jpg",
        "Beauty": "https://upload.wikimedia.org/wikipedia/commons/8/8f/Lakme_9_to_5_Scarlet_Surge_Primer%2BMatte_Lipstick_MR22.jpg",
        "Footwear": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/On_Clouds_running_shoes.jpg/960px-On_Clouds_running_shoes.jpg",
        "Jewellery": "https://upload.wikimedia.org/wikipedia/commons/b/b0/Golden_Plated_Bangle_remind_PS.jpg",
        "Grocery": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Boxes_of_green_grocery%2C_Lordship_Lane%2C_Tottenham%2C_London%2C_England.jpg/960px-Boxes_of_green_grocery%2C_Lordship_Lane%2C_Tottenham%2C_London%2C_England.jpg",
        "Sports": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1200&q=85",
        "Appliances": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Air_Purifier_%28Levoit_LV-H133%29_%2849317867758%29.jpg/960px-Air_Purifier_%28Levoit_LV-H133%29_%2849317867758%29.jpg",
        "Books": "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=1200&q=85",
    }

    UNSPLASH_IMAGES = {
        "Auraluxe Wireless Headphones": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Bose_QuietComfort_25_Acoustic_Noise_Cancelling_Headphones_with_Carry_Case.jpg/960px-Bose_QuietComfort_25_Acoustic_Noise_Cancelling_Headphones_with_Carry_Case.jpg",
        "Monarch Smart Watch Pro": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Huawei_Smartwatch_Fit_2.jpg/960px-Huawei_Smartwatch_Fit_2.jpg",
        "NovaBook Air 14 Laptop": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Schenker_VIA14_Laptop_asv2021-01.jpg/960px-Schenker_VIA14_Laptop_asv2021-01.jpg",
        "PixelPro 5G Smartphone": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Blackview_A60_Smartphone_Android_mobile_phone_front_face_logged_in_screen.jpg/960px-Blackview_A60_Smartphone_Android_mobile_phone_front_face_logged_in_screen.jpg",
        "Velvet Royale Evening Blazer": "https://images.unsplash.com/photo-1593030761757-71fae45fa0e7?auto=format&fit=crop&w=1200&q=85",
        "Maison Silk Saree Collection": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Sari_2.jpg/960px-Sari_2.jpg",
        "Astra Linen Resort Shirt": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Men%27s_Linen_Work_Shirt.jpg/960px-Men%27s_Linen_Work_Shirt.jpg",
        "Regal Leather Tote Bag": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Adele_Dejak_Tote_Bag_h014.jpg/960px-Adele_Dejak_Tote_Bag_h014.jpg",
        "NestAura Ceramic Dinner Set": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f1/Dinner_set_%28AM_2017.80.1-1%29.jpg/960px-Dinner_set_%28AM_2017.80.1-1%29.jpg",
        "CasaCloud Cotton Bedding Set": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=85",
        "LumaDecor Floor Lamp": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/EFTA00000289_-_Cozy_living_room_with_cream-colored_furniture_a_yellow_carpet_and_white_walls_featuring_a_sofa_armchair_floor_lamp_and_book_stack.jpg/960px-EFTA00000289_-_Cozy_living_room_with_cream-colored_furniture_a_yellow_carpet_and_white_walls_featuring_a_sofa_armchair_floor_lamp_and_book_stack.jpg",
        "LuxeGlow Vitamin C Serum": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=1200&q=85",
        "Veloura Matte Lip Kit": "https://upload.wikimedia.org/wikipedia/commons/8/8f/Lakme_9_to_5_Scarlet_Surge_Primer%2BMatte_Lipstick_MR22.jpg",
        "AquaBloom Hydrating Cream": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?auto=format&fit=crop&w=1200&q=85",
        "StrideX Running Shoes": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/On_Clouds_running_shoes.jpg/960px-On_Clouds_running_shoes.jpg",
        "CrownStep Leather Loafers": "https://upload.wikimedia.org/wikipedia/commons/f/f1/Loafers_for_Men_in_Black.jpg",
        "Auric Pearl Necklace": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ac/White_Wedding_-_pearl_necklace.jpg/960px-White_Wedding_-_pearl_necklace.jpg",
        "SonaCraft Gold Plated Bangles": "https://upload.wikimedia.org/wikipedia/commons/b/b0/Golden_Plated_Bangle_remind_PS.jpg",
        "Organic Pantry Essentials Box": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/61/Boxes_of_green_grocery%2C_Lordship_Lane%2C_Tottenham%2C_London%2C_England.jpg/960px-Boxes_of_green_grocery%2C_Lordship_Lane%2C_Tottenham%2C_London%2C_England.jpg",
        "Arabica Signature Coffee Beans": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Roasted_coffee_beans.jpg/960px-Roasted_coffee_beans.jpg",
        "FlexPro Yoga Mat": "https://images.unsplash.com/photo-1599901860904-17e6ed7083a0?auto=format&fit=crop&w=1200&q=85",
        "HydraSteel Sports Bottle": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Stainless_Steel_Water_Bottle.jpg/960px-Stainless_Steel_Water_Bottle.jpg",
        "PureAir Smart Air Purifier": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Air_Purifier_%28Levoit_LV-H133%29_%2849317867758%29.jpg/960px-Air_Purifier_%28Levoit_LV-H133%29_%2849317867758%29.jpg",
        "BrewMate Espresso Machine": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Espresso_machine_1.jpg/960px-Espresso_machine_1.jpg",
        "Atomic Habits Hardcover": "https://covers.openlibrary.org/b/isbn/9780735211292-L.jpg",
        "Designing Data Intensive Applications": "https://covers.openlibrary.org/b/isbn/9781449373320-L.jpg",
    }

    def _download_image(self, folder, slug, source_url):
        if not source_url:
            return ""
        media_dir = settings.MEDIA_ROOT / folder
        media_dir.mkdir(parents=True, exist_ok=True)
        try:
            response = requests.get(
                source_url,
                headers={"User-Agent": "LuxeNestDemo/1.0 (+local portfolio project)"},
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            self.stdout.write(self.style.WARNING(f"Could not download image for {slug}: {exc}"))
            return ""

        content_type = response.headers.get("content-type", "").split(";")[0].lower()
        extension = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }.get(content_type, Path(source_url.split("?")[0]).suffix.lower().lstrip(".") or "jpg")
        if extension == "jpeg":
            extension = "jpg"
        if extension not in {"jpg", "png", "webp"}:
            extension = "jpg"

        filename = f"{slug}-photo.{extension}"
        target = media_dir / filename
        target.write_bytes(response.content)
        return f"{folder}/{filename}"

    def _attach_product_photo(self, product, source_url=""):
        downloaded = self._download_image("products", product.slug, source_url)
        if downloaded:
            ProductImage.objects.update_or_create(
                product=product,
                is_primary=True,
                defaults={"image": downloaded, "alt_text": product.name},
            )
            product.external_image_url = ""
            product.save(update_fields=["external_image_url", "updated_at"])
            return
        if source_url:
            product.external_image_url = source_url
            product.save(update_fields=["external_image_url", "updated_at"])
            return
        for extension in ["jpg", "jpeg", "png", "webp"]:
            photo = settings.MEDIA_ROOT / "products" / f"{product.slug}-photo.{extension}"
            if photo.exists():
                ProductImage.objects.update_or_create(
                    product=product,
                    is_primary=True,
                    defaults={"image": f"products/{photo.name}", "alt_text": product.name},
                )
                product.external_image_url = ""
                product.save(update_fields=["external_image_url", "updated_at"])
                return
        self.stdout.write(self.style.WARNING(f"No real-world photo found for {product.name}; keeping existing image."))

    def _attach_category_photo(self, category, source_url=""):
        downloaded = self._download_image("categories", category.slug, source_url)
        if downloaded:
            category.image = downloaded
            category.external_image_url = ""
            category.save(update_fields=["image", "external_image_url"])
            return
        if source_url:
            category.external_image_url = source_url
            category.save(update_fields=["external_image_url"])
            return
        for extension in ["jpg", "jpeg", "png", "webp"]:
            photo = settings.MEDIA_ROOT / "categories" / f"{category.slug}-photo.{extension}"
            if photo.exists():
                category.image = f"categories/{photo.name}"
                category.external_image_url = ""
                category.save(update_fields=["image", "external_image_url"])
                return

    def handle(self, *args, **options):
        categories = {}
        category_names = [
            "Electronics",
            "Luxury Fashion",
            "Home Living",
            "Beauty",
            "Footwear",
            "Jewellery",
            "Grocery",
            "Sports",
            "Appliances",
            "Books",
        ]
        for category_name in category_names:
            category, _ = Category.objects.get_or_create(name=category_name, defaults={"is_featured": True})
            category.is_featured = True
            category.external_image_url = self.CATEGORY_IMAGES.get(category_name, "")
            category.save(update_fields=["is_featured", "external_image_url"])
            self._attach_category_photo(category, self.CATEGORY_IMAGES.get(category_name, ""))
            categories[category_name] = category

        products = [
            ("Auraluxe Wireless Headphones", "Electronics", "Auraluxe", 8999, 12999, 42, 4.7, "Adaptive noise cancellation, plush memory foam, and studio-grade wireless audio."),
            ("Monarch Smart Watch Pro", "Electronics", "Monarch", 11999, 16999, 31, 4.6, "AMOLED display, health sensors, Bluetooth calling, and seven-day battery life."),
            ("NovaBook Air 14 Laptop", "Electronics", "NovaBook", 58999, 74999, 21, 4.7, "Slim performance laptop with metal chassis, fast SSD storage, and all-day battery."),
            ("PixelPro 5G Smartphone", "Electronics", "PixelPro", 32999, 42999, 36, 4.5, "Flagship-grade 5G smartphone with AMOLED display and advanced camera system."),
            ("Velvet Royale Evening Blazer", "Luxury Fashion", "Velvet Royale", 7499, 10999, 18, 4.8, "Tailored luxury blazer with satin detailing and wrinkle-resistant premium fabric."),
            ("Maison Silk Saree Collection", "Luxury Fashion", "Maison", 9999, 14999, 15, 4.9, "Elegant woven silk saree with gold-toned accents and refined drape."),
            ("Astra Linen Resort Shirt", "Luxury Fashion", "Astra", 2199, 3499, 64, 4.3, "Breathable linen shirt designed for premium casual styling and warm-weather comfort."),
            ("Regal Leather Tote Bag", "Luxury Fashion", "Regal", 5499, 7999, 24, 4.6, "Structured leather tote with polished hardware, laptop sleeve, and daily carry space."),
            ("NestAura Ceramic Dinner Set", "Home Living", "NestAura", 4999, 7499, 26, 4.5, "A premium 24-piece ceramic dinner set for modern dining spaces."),
            ("CasaCloud Cotton Bedding Set", "Home Living", "CasaCloud", 3499, 5299, 40, 4.4, "Soft cotton bedsheet and pillow set with a crisp hotel-style finish."),
            ("LumaDecor Floor Lamp", "Home Living", "LumaDecor", 2899, 4299, 33, 4.2, "Minimal floor lamp with warm light output for living rooms and reading corners."),
            ("LuxeGlow Vitamin C Serum", "Beauty", "LuxeGlow", 1499, 2299, 60, 4.4, "Brightening daily serum with stable vitamin C and hyaluronic hydration."),
            ("Veloura Matte Lip Kit", "Beauty", "Veloura", 999, 1599, 88, 4.3, "Long-wear matte lip color kit with rich pigment and comfortable finish."),
            ("AquaBloom Hydrating Cream", "Beauty", "AquaBloom", 1299, 1999, 72, 4.5, "Daily moisturizer with lightweight hydration and barrier-supporting ingredients."),
            ("StrideX Running Shoes", "Footwear", "StrideX", 3999, 5999, 48, 4.4, "Responsive running shoes with breathable mesh and cushioned support."),
            ("CrownStep Leather Loafers", "Footwear", "CrownStep", 4599, 6999, 28, 4.6, "Polished leather loafers with cushioned insole and formal-ready silhouette."),
            ("Auric Pearl Necklace", "Jewellery", "Auric", 2999, 4999, 22, 4.7, "Elegant pearl necklace with gold-toned clasp for occasion styling."),
            ("SonaCraft Gold Plated Bangles", "Jewellery", "SonaCraft", 1799, 2899, 45, 4.4, "Set of gold plated bangles with festive detailing and premium finish."),
            ("Organic Pantry Essentials Box", "Grocery", "PureNest", 1499, 2199, 95, 4.2, "Curated grocery box with premium staples, nuts, seeds, and pantry essentials."),
            ("Arabica Signature Coffee Beans", "Grocery", "BeanVault", 899, 1299, 110, 4.6, "Fresh roasted arabica coffee beans with rich aroma and smooth finish."),
            ("FlexPro Yoga Mat", "Sports", "FlexPro", 1199, 1899, 58, 4.4, "Anti-slip yoga mat with high-density cushioning and carry strap."),
            ("HydraSteel Sports Bottle", "Sports", "HydraSteel", 799, 1199, 120, 4.3, "Insulated stainless steel bottle for gym, travel, and daily hydration."),
            ("PureAir Smart Air Purifier", "Appliances", "PureAir", 13999, 18999, 17, 4.6, "Smart air purifier with HEPA filtration, app control, and quiet night mode."),
            ("BrewMate Espresso Machine", "Appliances", "BrewMate", 9999, 14999, 19, 4.5, "Compact espresso machine for cafe-style coffee at home."),
            ("Atomic Habits Hardcover", "Books", "LuxeReads", 499, 799, 90, 4.8, "Bestselling personal growth book in a premium hardcover edition."),
            ("Designing Data Intensive Applications", "Books", "TechShelf", 1299, 1899, 34, 4.9, "Deep technical guide for scalable systems, data storage, and distributed architecture."),
        ]

        for name, category, brand, price, mrp, stock, rating, description in products:
            product, _ = Product.objects.update_or_create(
                name=name,
                defaults={
                    "category": categories[category],
                    "brand": brand,
                    "price": Decimal(price),
                    "mrp": Decimal(mrp),
                    "stock": stock,
                    "rating": Decimal(str(rating)),
                    "review_count": stock * 3,
                    "description": description,
                    "external_image_url": self.UNSPLASH_IMAGES.get(name, ""),
                    "is_featured": True,
                    "is_trending": stock % 2 == 0,
                    "is_active": True,
                },
            )
            ProductVariant.objects.get_or_create(product=product, name="Color", value="Signature Blue")
            ProductVariant.objects.get_or_create(product=product, name="Warranty", value="1 Year LuxeCare")
            self._attach_product_photo(product, self.UNSPLASH_IMAGES.get(name, ""))

        Coupon.objects.update_or_create(
            code="LUXE10",
            defaults={
                "description": "10% launch discount",
                "discount_percent": 10,
                "max_discount": Decimal("1000.00"),
                "minimum_order_value": Decimal("1999.00"),
                "is_active": True,
                "valid_from": timezone.now() - timedelta(days=1),
                "valid_until": timezone.now() + timedelta(days=90),
            },
        )

        self.stdout.write(self.style.SUCCESS("LuxeNest demo catalog seeded."))
