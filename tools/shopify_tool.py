import os
import shopify
from dotenv import load_dotenv

load_dotenv()

SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-01")


def connect_shopify():
    if not SHOP_URL or not ACCESS_TOKEN:
        raise ValueError("SHOPIFY_SHOP_URL en SHOPIFY_ACCESS_TOKEN ontbreken in .env")

    session = shopify.Session(SHOP_URL, API_VERSION, ACCESS_TOKEN)
    shopify.ShopifyResource.activate_session(session)
    return shopify.Shop.current()


def test_shopify():
    shop = connect_shopify()
    return {
        "name": shop.name,
        "domain": shop.domain,
        "email": getattr(shop, "email", None)
    }


def create_product(title, body_html="", vendor="Wilbert", product_type="Dropshipping", price="19.99", image_url=None):
    connect_shopify()

    product = shopify.Product()
    product.title = title
    product.body_html = body_html
    product.vendor = vendor
    product.product_type = product_type
    product.status = "active"

    variant = shopify.Variant()
    variant.price = price
    product.variants = [variant]

    if image_url:
        image = shopify.Image()
        image.src = image_url
        product.images = [image]

    if product.save():
        return {
            "ok": True,
            "id": product.id,
            "title": product.title
        }

    return {
        "ok": False,
        "errors": product.errors.full_messages()
    }


def create_page(title, body_html):
    connect_shopify()

    page = shopify.Page()
    page.title = title
    page.body_html = body_html
    page.published = True

    if page.save():
        return {
            "ok": True,
            "id": page.id,
            "title": page.title
        }

    return {
        "ok": False,
        "errors": page.errors.full_messages()
    }


def create_collection(title, body_html=""):
    connect_shopify()

    collection = shopify.CustomCollection()
    collection.title = title
    collection.body_html = body_html
    collection.published = True

    if collection.save():
        return {
            "ok": True,
            "id": collection.id,
            "title": collection.title
        }

    return {
        "ok": False,
        "errors": collection.errors.full_messages()
    }


def list_products(limit=10):
    connect_shopify()

    products = shopify.Product.find(limit=limit)

    return [
        {
            "id": p.id,
            "title": p.title,
            "vendor": p.vendor,
            "product_type": p.product_type,
            "status": getattr(p, "status", None)
        }
        for p in products
    ]


def setup_dropshipping_store():
    connect_shopify()

    created = []

    created.append(create_page(
        "Over ons",
        "<h1>Over ons</h1><p>Wij helpen klanten slimme, moderne producten ontdekken voor dagelijks gebruik.</p>"
    ))

    created.append(create_page(
        "Verzending",
        "<h1>Verzending</h1><p>Bestellingen worden zorgvuldig verwerkt en geleverd via onze logistieke partners.</p>"
    ))

    created.append(create_page(
        "Contact",
        "<h1>Contact</h1><p>Neem contact met ons op voor vragen over je bestelling of onze producten.</p>"
    ))

    created.append(create_collection(
        "Populaire producten",
        "<p>Onze meest populaire dropshipping producten.</p>"
    ))

    return {
        "ok": True,
        "created": created
    }
