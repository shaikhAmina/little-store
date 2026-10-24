"""Pure, testable helpers for the Little Store app.

Kept free of Streamlit/Supabase imports so image-compression and
PDF logic can be unit-tested in isolation.
"""

import io
import urllib.request
from datetime import datetime
from decimal import Decimal

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, HRFlowable, KeepTogether,
)


# ─────────────────────────────────────────────────────────────
# Money helpers
# ─────────────────────────────────────────────────────────────

def money(value) -> str:
    """Format a number as Indian Rupees for the on-screen UI.
    Returns 'Contact for price' when value is None."""
    if value is None:
        return "Contact for price"
    try:
        v = Decimal(str(value))
    except Exception:
        return "Contact for price"
    return f"₹{v:,.2f}"


def money_pdf(value) -> str:
    """Rupee formatting for the PDF (reportlab default font lacks ₹ glyph).
    Returns 'Contact for price' when value is None."""
    if value is None:
        return "Contact for price"
    try:
        v = Decimal(str(value))
    except Exception:
        return "Contact for price"
    return f"Rs. {v:,.2f}"


# ─────────────────────────────────────────────────────────────
# Image compression (quality-preserving)
# ─────────────────────────────────────────────────────────────

MAX_IMAGE_DIMENSION = 1600
JPEG_QUALITY        = 85
WEBP_QUALITY        = 85

IMAGE_SUFFIXES = {"png", "jpg", "jpeg", "webp", "gif"}
VIDEO_SUFFIXES = {"mp4", "mov", "webm"}
CONTENT_TYPES  = {
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
    "webp": "image/webp",
    "gif":  "image/gif",
    "mp4":  "video/mp4",
    "mov":  "video/quicktime",
    "webm": "video/webm",
}


def compress_image(file_bytes: bytes, filename: str) -> tuple[bytes, str]:
    """Compress an image while keeping good visual quality for a store catalogue.

    - GIFs are passed through unchanged so animation is preserved.
    - Oversized images are downscaled to MAX_IMAGE_DIMENSION on the longest side.
    - JPEG/WEBP are re-encoded at quality 85; PNG is re-saved optimised.

    Returns (compressed_bytes, new_extension).
    """
    original_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"

    if original_ext == "gif":
        return file_bytes, "gif"

    try:
        img = Image.open(io.BytesIO(file_bytes))
    except Exception:
        return file_bytes, original_ext

    img = ImageOps.exif_transpose(img)

    if max(img.size) > MAX_IMAGE_DIMENSION:
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

    if original_ext == "png":
        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue(), "png"

    if original_ext == "webp":
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
        return out.getvalue(), "webp"

    if img.mode in ("RGBA", "P", "LA", "L"):
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    return out.getvalue(), "jpg"


# ─────────────────────────────────────────────────────────────
# Shared PDF helpers
# ─────────────────────────────────────────────────────────────

_PDF_THUMB_MAX_PX = 700


def fetch_image_bytes(url: str, timeout: int = 15) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def _make_thumbnail(image_bytes: bytes, max_px: int = _PDF_THUMB_MAX_PX) -> io.BytesIO | None:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        if max(img.size) > max_px:
            img.thumbnail((max_px, max_px), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85)
        out.seek(0)
        return out
    except Exception:
        return None


def _rl_image(url: str | None, w_mm: float, h_mm: float, styles) -> object:
    """Fetch URL and return an RLImage or fallback Paragraph."""
    small = styles["small"] if "small" in styles.byName else styles["Normal"]
    if url:
        raw = fetch_image_bytes(url)
        if raw:
            thumb = _make_thumbnail(raw)
            if thumb:
                try:
                    return RLImage(thumb, width=w_mm * mm, height=h_mm * mm, kind="proportional")
                except Exception:
                    pass
    return Paragraph("[ No image ]", small)


# ─────────────────────────────────────────────────────────────
# Cart PDF  (customer download – shows cart items + total)
# ─────────────────────────────────────────────────────────────

def build_cart_pdf(items: list, total, store_name: str = "Little Store") -> bytes:
    """Build a catalogue-style cart PDF.

    Each item dict: name, description, price, quantity, image_url.
    price may be None (contact for price).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=18 * mm, bottomMargin=15 * mm,
    )
    S = getSampleStyleSheet()
    S.add(ParagraphStyle("pname",  parent=S["Normal"], fontName="Helvetica-Bold",
                         fontSize=12, leading=15, textColor=colors.HexColor("#111111")))
    S.add(ParagraphStyle("small",  parent=S["Normal"], fontSize=9,
                         textColor=colors.HexColor("#444444"), leading=12))
    S.add(ParagraphStyle("ptotal", parent=S["Normal"], fontName="Helvetica-Bold", fontSize=13))

    story: list = [
        Paragraph(store_name, S["Title"]),
        Paragraph("Shopping Cart Summary", S["Heading2"]),
        Paragraph(datetime.now().strftime("%d %b %Y, %I:%M %p"), S["small"]),
        Spacer(1, 6 * mm),
    ]

    if not items:
        story.append(Paragraph("Your cart is empty.", S["Normal"]))
    else:
        for it in items:
            price_raw = it.get("price")
            qty       = int(it.get("quantity", 1))
            if price_raw is not None:
                price = Decimal(str(price_raw))
                line  = price * qty
                price_line = f"{money_pdf(price)} × {qty} = <b>{money_pdf(line)}</b>"
            else:
                price_line = "Contact for price"

            img_cell = _rl_image(it.get("image_url"), 45, 40, S)
            text_cell = [
                Paragraph(it.get("name", ""), S["pname"]),
                Spacer(1, 1 * mm),
                Paragraph(it.get("description", "") or "", S["small"]),
                Spacer(1, 2 * mm),
                Paragraph(price_line, S["Normal"]),
            ]
            row = Table([[img_cell, text_cell]], colWidths=[50 * mm, 130 * mm])
            row.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("LEFTPADDING",   (0, 0), (-1, -1), 4),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story += [row, Spacer(1, 3 * mm)]

    story += [
        Spacer(1, 4 * mm),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#999999")),
        Spacer(1, 2 * mm),
        Paragraph(f"Total: {money_pdf(total)}", S["ptotal"]),
        Spacer(1, 3 * mm),
        Paragraph("Cash on Delivery · Pay when your order arrives.", S["small"]),
    ]

    doc.build(story)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────────
# Admin Catalogue PDF  (all products with full details)
# ─────────────────────────────────────────────────────────────

def build_catalogue_pdf(products: list, store_name: str = "Little Store") -> bytes:
    """Build a product-catalogue PDF for the admin.

    Each product dict:
        name, description, price (None OK), original_price (None OK),
        category, image_url (primary image).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=18 * mm, bottomMargin=15 * mm,
    )
    S = getSampleStyleSheet()
    # register only if not already present
    for name, kwargs in [
        ("cat_name", dict(parent=S["Normal"], fontName="Helvetica-Bold",
                          fontSize=13, leading=16, textColor=colors.HexColor("#111111"))),
        ("sale_tag", dict(parent=S["Normal"], fontName="Helvetica-Bold",
                          fontSize=9,  textColor=colors.HexColor("#c0392b"))),
        ("orig",     dict(parent=S["Normal"], fontSize=9,
                          textColor=colors.HexColor("#888888"))),
        ("small",    dict(parent=S["Normal"], fontSize=9,
                          textColor=colors.HexColor("#444444"), leading=12)),
        ("cat_tag",  dict(parent=S["Normal"], fontSize=8,
                          textColor=colors.HexColor("#2563eb"))),
    ]:
        if name not in S.byName:
            S.add(ParagraphStyle(name, **kwargs))

    story: list = [
        Paragraph(store_name, S["Title"]),
        Paragraph("Product Catalogue", S["Heading2"]),
        Paragraph(
            f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}  ·  "
            f"{len(products)} product(s)",
            S["small"],
        ),
        Spacer(1, 8 * mm),
    ]

    for p in products:
        name         = p.get("name", "")
        desc         = p.get("description", "") or ""
        price_raw    = p.get("price")
        orig_raw     = p.get("original_price")
        category     = p.get("category") or ""
        img_url      = p.get("image_url")
        on_sale      = orig_raw is not None and price_raw is not None and Decimal(str(orig_raw)) > Decimal(str(price_raw))

        # Image cell
        img_cell = _rl_image(img_url, 50, 50, S)

        # Text cell
        texts: list = [Paragraph(name, S["cat_name"])]
        if category:
            texts += [Spacer(1, 1 * mm), Paragraph(f"Category: {category}", S["cat_tag"])]
        texts.append(Spacer(1, 2 * mm))
        if on_sale:
            texts.append(Paragraph("🔖 ON SALE", S["sale_tag"]))
            texts.append(Paragraph(f"Sale price:  {money_pdf(price_raw)}", S["Normal"]))
            texts.append(Paragraph(f"Was:  {money_pdf(orig_raw)}", S["orig"]))
        else:
            texts.append(Paragraph(money_pdf(price_raw), S["Normal"]))
        if desc:
            texts += [Spacer(1, 2 * mm), Paragraph(desc, S["small"])]

        row = Table([[img_cell, texts]], colWidths=[55 * mm, 125 * mm])
        row.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("BOX",           (0, 0), (-1, -1), 0.6, colors.HexColor("#cccccc")),
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#fafafa")),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story += [KeepTogether([row, Spacer(1, 4 * mm)])]

    story += [
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")),
        Spacer(1, 2 * mm),
        Paragraph(f"Total products: {len(products)}", S["small"]),
    ]

    doc.build(story)
    return buffer.getvalue()
