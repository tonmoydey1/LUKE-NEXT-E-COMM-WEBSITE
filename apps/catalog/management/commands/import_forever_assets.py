import re
import shutil
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.catalog.models import Category, Product, ProductImage, ProductVariant


class Command(BaseCommand):
    help = "Import the Forever asset pack into LuxeNest with matching product images."

    FRONTEND_ASSET_DIR = Path(r"C:\Users\Tonmoy Dey\Downloads\forever-assets\assets\frontend_assets")
    ADMIN_ASSET_DIR = Path(r"C:\Users\Tonmoy Dey\Downloads\forever-assets\assets\admin_assets")

    BRAND_BY_CATEGORY = {
        "Men": "LuxeNest Men",
        "Women": "LuxeNest Women",
        "Kids": "LuxeNest Kids",
    }

    CATEGORY_IMAGES = {
        "Men": "p_img38.png",
        "Women": "p_img54.png",
        "Kids": "p_img36.png",
    }

    def handle(self, *args, **options):
        frontend_dir = self.FRONTEND_ASSET_DIR
        admin_dir = self.ADMIN_ASSET_DIR
        if not frontend_dir.exists():
            frontend_dir = settings.BASE_DIR / "static" / "forever-assets" / "frontend_assets"
        if not admin_dir.exists():
            admin_dir = settings.BASE_DIR / "static" / "forever-assets" / "admin_assets"
        if not frontend_dir.exists():
            raise CommandError(f"Frontend asset folder not found: {frontend_dir}")
        if not admin_dir.exists():
            raise CommandError(f"Admin asset folder not found: {admin_dir}")
        self.FRONTEND_ASSET_DIR = frontend_dir
        self.ADMIN_ASSET_DIR = admin_dir

        asset_js = frontend_dir / "assets.js"
        text = asset_js.read_text(encoding="utf-8")
        imports = self._parse_imports(text)
        products = self._parse_products(text, imports)

        self._copy_static_asset_pack(self.FRONTEND_ASSET_DIR, "frontend_assets")
        self._copy_static_asset_pack(self.ADMIN_ASSET_DIR, "admin_assets")

        categories = self._ensure_categories(products)
        imported_count = 0
        for product_data in products:
            self._upsert_product(product_data, categories)
            imported_count += 1

        self._attach_category_images(categories)
        self.stdout.write(self.style.SUCCESS(f"Imported {imported_count} Forever products with matching images."))

    def _parse_imports(self, text):
        return dict(re.findall(r"import\s+(\w+)\s+from\s+'\.\/([^']+)'", text))

    def _parse_products(self, text, imports):
        product_text = text.split("export const products = [", 1)[1].rsplit("]", 1)[0]
        blocks = re.findall(r"\{\s*_id:.*?\n\s*\}", product_text, flags=re.S)
        products = []
        for block in blocks:
            source_id = self._field(block, "_id")
            name = self._field(block, "name")
            description = self._field(block, "description")
            category = self._field(block, "category")
            subcategory = self._field(block, "subCategory")
            price = self._number_field(block, "price")
            bestseller = self._bool_field(block, "bestseller")
            image_vars = self._image_vars(block)
            image_files = [imports[var] for var in image_vars if var in imports]
            sizes = self._sizes(block)
            if not all([source_id, name, category, subcategory]) or not image_files:
                self.stdout.write(self.style.WARNING(f"Skipped incomplete product block: {name or source_id or 'unknown'}"))
                continue
            products.append(
                {
                    "source_id": source_id,
                    "name": name,
                    "description": description,
                    "category": category,
                    "subcategory": subcategory,
                    "price": price,
                    "bestseller": bestseller,
                    "image_files": image_files,
                    "sizes": sizes,
                }
            )
        return products

    def _field(self, block, field):
        match = re.search(rf'{field}:\s*"([^"]*)"', block)
        return match.group(1).strip() if match else ""

    def _number_field(self, block, field):
        match = re.search(rf"{field}:\s*(\d+)", block)
        return Decimal(match.group(1)) if match else Decimal("0")

    def _bool_field(self, block, field):
        match = re.search(rf"{field}:\s*(true|false)", block)
        return bool(match and match.group(1) == "true")

    def _image_vars(self, block):
        match = re.search(r"image:\s*\[([^\]]+)\]", block)
        if not match:
            return []
        return [item.strip() for item in match.group(1).split(",") if item.strip()]

    def _sizes(self, block):
        match = re.search(r"sizes:\s*\[([^\]]+)\]", block)
        if not match:
            return []
        return [size.strip().strip('"') for size in match.group(1).split(",") if size.strip()]

    def _copy_static_asset_pack(self, source_dir, folder_name):
        target_dir = settings.BASE_DIR / "static" / "forever-assets" / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in source_dir.iterdir():
            if source.is_file():
                target = target_dir / source.name
                if source.resolve() != target.resolve():
                    shutil.copy2(source, target)

    def _ensure_categories(self, products):
        categories = {}
        for product in products:
            parent_name = product["category"]
            parent, _ = Category.objects.update_or_create(
                slug=slugify(parent_name),
                defaults={"name": parent_name, "is_featured": True, "external_image_url": ""},
            )
            leaf_name = f"{parent_name} {product['subcategory']}"
            leaf, _ = Category.objects.update_or_create(
                slug=slugify(leaf_name),
                defaults={"name": leaf_name, "parent": parent, "is_featured": False, "external_image_url": ""},
            )
            categories[parent_name] = parent
            categories[leaf_name] = leaf
        return categories

    def _upsert_product(self, product_data, categories):
        category = categories[f"{product_data['category']} {product_data['subcategory']}"]
        slug = f"forever-{product_data['source_id']}"
        price = product_data["price"] * Decimal("10")
        mrp = (price * Decimal("1.65")).quantize(Decimal("1.00"))
        rating_seed = (sum(ord(char) for char in product_data["source_id"]) % 6) / 10
        rating = Decimal(str(4.3 + rating_seed)).quantize(Decimal("1.00"))
        review_count = 40 + (sum(ord(char) for char in product_data["name"]) % 190)

        product, _ = Product.objects.update_or_create(
            slug=slug,
            defaults={
                "category": category,
                "name": product_data["name"],
                "brand": self.BRAND_BY_CATEGORY.get(product_data["category"], "LuxeNest"),
                "description": self._polished_description(product_data),
                "price": price,
                "mrp": mrp,
                "gst_rate": Decimal("18.00"),
                "stock": 50 if product_data["bestseller"] else 28,
                "rating": rating,
                "review_count": review_count,
                "external_image_url": "",
                "is_featured": product_data["bestseller"],
                "is_trending": product_data["subcategory"] in {"Topwear", "Winterwear"},
                "is_active": True,
            },
        )

        ProductImage.objects.filter(product=product).delete()
        for index, filename in enumerate(product_data["image_files"]):
            relative_path = self._copy_product_image(filename)
            ProductImage.objects.create(
                product=product,
                image=relative_path,
                alt_text=f"{product_data['name']} - view {index + 1}",
                is_primary=index == 0,
            )

        ProductVariant.objects.filter(product=product).delete()
        for size in product_data["sizes"]:
            ProductVariant.objects.create(product=product, name="Size", value=size, stock=20)
        ProductVariant.objects.create(product=product, name="Collection", value=product_data["subcategory"], stock=product.stock)

    def _copy_product_image(self, filename):
        source = self.FRONTEND_ASSET_DIR / filename
        target_dir = settings.MEDIA_ROOT / "products" / "forever"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        shutil.copy2(source, target)
        return f"products/forever/{filename}"

    def _attach_category_images(self, categories):
        for category_name, filename in self.CATEGORY_IMAGES.items():
            category = categories.get(category_name)
            if not category:
                continue
            source = self.FRONTEND_ASSET_DIR / filename
            if not source.exists():
                continue
            target_dir = settings.MEDIA_ROOT / "categories"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"forever-{slugify(category_name)}{source.suffix}"
            shutil.copy2(source, target)
            category.image = f"categories/{target.name}"
            category.external_image_url = ""
            category.is_featured = True
            category.save(update_fields=["image", "external_image_url", "is_featured"])

    def _polished_description(self, product_data):
        audience = {"Men": "men", "Women": "women", "Kids": "kids"}.get(product_data["category"], "shoppers")
        return (
            f"Premium {product_data['subcategory'].lower()} for {audience}, tailored for everyday comfort, "
            "clean styling, and reliable LuxeNest delivery. The product photo is mapped directly from the "
            "matching catalog asset so the listing, detail page, cart, wishlist, and invoice stay consistent."
        )
