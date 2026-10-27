import os
import uuid
from decimal import Decimal, InvalidOperation

import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client

from store_utils import (
    money, money_pdf,
    compress_image, build_cart_pdf, build_catalogue_pdf,
    IMAGE_SUFFIXES, VIDEO_SUFFIXES, CONTENT_TYPES,
)

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Little Store",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #faf8ff;
}
/* Give the catalogue room on desktop while keeping mobile cards compact. */
.block-container {
    padding-top: 1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 1180px !important;
    margin: 0 auto !important;
}
/* hide sidebar toggle */
[data-testid="collapsedControl"] { display:none !important; }
[data-testid="stSidebar"]        { display:none !important; }

/* ── Top navbar ── */
.topnav {
    display:flex; align-items:center; justify-content:space-between;
    background:#101827;
    padding:0 22px; height:60px;
    border-radius:14px;
    margin-bottom:20px;
    box-shadow:0 8px 24px rgba(16,24,39,.14);
}
.topnav-left  { display:flex; align-items:center; gap:10px; }
.topnav-logo  { height:32px; width:32px; border-radius:6px; object-fit:cover; }
.topnav-brand { color:#fff; font-size:1.05rem; font-weight:800; white-space:nowrap; }
.topnav-links { display:flex; gap:2px; }
.topnav-links a {
    color:rgba(255,255,255,.75); text-decoration:none;
    padding:5px 13px; border-radius:8px;
    font-size:.875rem; font-weight:500;
    transition:background .15s,color .15s;
}
.topnav-links a:hover  { background:rgba(255,255,255,.15); color:#fff; }
.topnav-links a.active { background:rgba(255,255,255,.25); color:#fff; font-weight:700; }
.topnav-cart {
    color:#101827; background:#a5f3fc; border-radius:20px;
    padding:6px 14px; font-size:.82rem; font-weight:800; white-space:nowrap;
}

/* ── Contact strip ── */
.contact-bar {
    background:#f5f3ff; border:1px solid #ddd6fe;
    border-radius:10px; padding:7px 16px;
    font-size:.83rem; color:#5b21b6;
    display:flex; gap:18px; align-items:center;
    flex-wrap:wrap; margin-bottom:14px; line-height:1.6;
}
.contact-bar a { color:#7c3aed; font-weight:600; text-decoration:none; }

/* ── Hero ── */
.hero {
    position:relative; overflow:hidden;
    background:radial-gradient(ellipse at 88% 15%,rgba(34,211,238,.27),transparent 33%),
               linear-gradient(120deg,#101827 0%,#172b46 58%,#164e63 100%);
    border-radius:20px; padding:30px 32px;
    margin-bottom:20px; color:#fff;
    box-shadow:0 16px 38px rgba(16,24,39,.16);
}
.hero-inner { display:flex; align-items:center; gap:16px; }
.hero-logo   { height:52px; width:52px; border-radius:10px; object-fit:cover;
               border:2px solid rgba(255,255,255,.35); flex-shrink:0; }
.hero-kicker {
    display:inline-block; margin-bottom:8px; color:#a5f3fc;
    font-size:.7rem; font-weight:800; letter-spacing:.14em;
}
.hero h1 { margin:0 0 6px; font-size:clamp(1.65rem,4vw,2.45rem); font-weight:850; letter-spacing:-.04em; }
.hero p  { margin:0; max-width:560px; font-size:.98rem; opacity:.84; line-height:1.5; }

/* ── Section title ── */
.section-title {
    font-size:1.15rem; font-weight:800; color:#101827;
    margin:22px 0 12px; border-left:4px solid #06b6d4; padding-left:10px;
}

/* ── Filter bar ── */
.filter-bar, .st-key-store-filters {
    background:#fff; border:1px solid #e2e8f0;
    border-radius:14px; padding:10px 12px; margin-bottom:16px;
    box-shadow:0 4px 16px rgba(15,23,42,.045);
}

/* ── Product card ── */
.pc-outer {
    border:1px solid #e2e8f0; border-radius:14px;
    overflow:hidden; background:#fff;
    box-shadow:0 2px 8px rgba(0,0,0,.05);
    transition:box-shadow .2s,transform .2s;
}
.pc-outer:hover {
    box-shadow:0 8px 24px rgba(124,58,237,.15);
    transform:translateY(-2px);
}
.pc-body { padding:10px 13px 14px; }
.pc-cat  {
    display:inline-block; background:#f5f3ff; color:#7c3aed;
    font-size:.68rem; font-weight:700; border-radius:20px;
    padding:2px 9px; margin-bottom:6px;
}
.pc-name {
    font-size:.95rem; font-weight:700; color:#1e1b4b;
    margin:0 0 4px; line-height:1.35;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;
    overflow:hidden; min-height:2.55rem;
}
.pc-price   { font-size:1.15rem; font-weight:800; color:#7c3aed; }
.pc-orig    { font-size:.78rem; color:#94a3b8; text-decoration:line-through; margin-left:5px; }
.pc-contact { font-size:.85rem; color:#64748b; font-style:italic; }
.badge-sale {
    display:inline-block;
    background:linear-gradient(90deg,#ef4444,#f97316);
    color:#fff; font-size:.65rem; font-weight:700;
    border-radius:20px; padding:2px 8px; margin-right:4px;
}

/* ── Cart ── */
.total-box {
    background:linear-gradient(135deg,#f5f3ff 0%,#ede9fe 100%);
    border:1px solid #ddd6fe; border-radius:12px;
    padding:12px 18px; margin:10px 0;
}
.total-label  { font-size:.8rem; color:#6d28d9; margin:0; }
.total-amount { font-size:1.6rem; font-weight:800; color:#4c1d95; margin:0; }

/* ── Order card ── */
.order-card {
    background:#fff; border:1.5px solid #ddd6fe;
    border-radius:14px; padding:18px;
    box-shadow:0 2px 12px rgba(124,58,237,.08);
}

/* ── Admin stat ── */
.admin-stat {
    background:#fff; border:1px solid #ddd6fe;
    border-radius:12px; padding:14px 16px; text-align:center;
    box-shadow:0 1px 4px rgba(0,0,0,.04);
}
.admin-stat .sn { font-size:1.7rem; font-weight:800; color:#7c3aed; }
.admin-stat .sl { font-size:.78rem; color:#6d28d9; margin-top:2px; }

/* ── Status pills ── */
.status-pill { display:inline-block; border-radius:20px; padding:2px 10px; font-size:.74rem; font-weight:700; }
.status-pending    { background:#fef3c7; color:#92400e; }
.status-confirmed  { background:#ede9fe; color:#5b21b6; }
.status-processing { background:#f3e8ff; color:#6d28d9; }
.status-shipped    { background:#d1fae5; color:#065f46; }
.status-delivered  { background:#bbf7d0; color:#14532d; }
.status-cancelled  { background:#fee2e2; color:#991b1b; }

/* ── Misc ── */
.nice-divider { border:none; border-top:1px solid #ddd6fe; margin:20px 0; }
.empty-cart   { text-align:center; padding:32px 0; color:#a78bfa; font-size:.95rem; }

/* ── Buttons ── */
.stButton>button[kind="primary"] {
    background:#101827 !important;
    border:none !important; border-radius:9px !important;
    font-weight:600 !important; letter-spacing:.2px;
    color:#fff !important;
}
.stButton>button[kind="secondary"] {
    border-radius:9px !important; font-weight:600 !important;
    border:1px solid #dbe3eb !important; color:#334155 !important;
}
.stDownloadButton>button {
    background:linear-gradient(90deg,#059669,#0d9488) !important;
    color:#fff !important; border:none !important;
    border-radius:8px !important; font-weight:600 !important;
}
/* Keep product rows aligned with the two-column layout at every screen size. */
[data-testid="stColumn"] { padding-left:3px !important; padding-right:3px !important; }
[data-testid="stNumberInput"] { max-width:100%; }
[class*="st-key-product-row-"] [data-testid="stHorizontalBlock"] {
    display:grid !important;
    grid-template-columns:repeat(2,minmax(0,1fr)) !important;
    gap:10px !important;
}
[class*="st-key-product-row-"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    width:100% !important;
    min-width:0 !important;
    flex:none !important;
}
[class*="st-key-product-row-"] [data-testid="stVerticalBlock"] {
    gap:.55rem !important;
}
[class*="st-key-product-row-"] [data-testid="stImage"] {
    background:#f6f8fa;
    border-radius:12px;
    overflow:hidden;
}
[class*="st-key-product-row-"] [data-testid="stImage"] img {
    height:170px !important;
    object-fit:contain !important;
}
[class*="st-key-product-row-"] [data-testid="stVerticalBlockBorderWrapper"] {
    height:100%;
    border:1px solid #e5eaf0 !important;
    border-radius:16px !important;
    background:#fff !important;
    box-shadow:0 4px 16px rgba(15,23,42,.045);
    transition:transform .18s ease,box-shadow .18s ease;
}
[class*="st-key-product-row-"] [data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform:translateY(-3px);
    box-shadow:0 12px 28px rgba(15,23,42,.11);
}

@media (max-width: 640px) {
    .block-container {
        padding: .55rem .45rem 1.5rem !important;
    }
    .topnav {
        height:52px;
        padding:0 13px;
        border-radius:0 0 13px 13px;
        margin:-.55rem -.45rem 14px;
    }
    .hero {
        border-radius:15px;
        padding:20px 17px;
        margin-bottom:14px;
    }
    .hero-logo { height:42px; width:42px; }
    .hero p { font-size:.84rem; }
    .filter-bar { padding:7px; }
    [class*="st-key-store-filters"] [data-testid="stHorizontalBlock"] {
        display:grid !important;
        grid-template-columns:repeat(2,minmax(0,1fr)) !important;
        gap:6px !important;
    }
    [class*="st-key-store-filters"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        width:100% !important;
        min-width:0 !important;
        flex:none !important;
    }
    [class*="st-key-store-filters"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
        grid-column:1 / -1;
    }
    [class*="st-key-product-row-"] [data-testid="stHorizontalBlock"] { gap:7px !important; }
    [class*="st-key-product-row-"] [data-testid="stImage"] img {
        height:112px !important;
    }
    [class*="st-key-product-row-"] .stButton button {
        min-height:2.25rem;
        padding:.35rem .18rem !important;
        font-size:.72rem !important;
    }
    [class*="st-key-product-row-"] [data-testid="stVerticalBlockBorderWrapper"] { border-radius:13px !important; }
}

@media (min-width: 641px) and (max-width: 900px) {
    [class*="st-key-product-row-"] [data-testid="stImage"] img { height:150px !important; }
}

/* ── Nav tabs — purple dark bar ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background:#101827;
    border-radius:13px;
    padding:6px 12px; gap:4px;
    border-bottom:none !important;
    margin-bottom:16px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    color:rgba(255,255,255,.75) !important;
    font-weight:500 !important; font-size:.88rem !important;
    padding:8px 16px !important; border-radius:8px !important;
    border:none !important; background:transparent !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    background:rgba(255,255,255,.15) !important; color:#fff !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background:#164e63 !important;
    color:#fff !important; font-weight:700 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display:none !important; }
</style>

""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Settings / Supabase
# ─────────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    try:
        value = st.secrets[key]
        if value:
            return str(value)
    except (KeyError, FileNotFoundError):
        pass
    except Exception as exc:
        if exc.__class__.__name__ != "StreamlitSecretNotFoundError":
            raise
    return os.getenv(key, default)

def get_supabase() -> Client | None:
    url = get_setting("SUPABASE_URL")
    key = get_setting("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def admin_password() -> str:
    return get_setting("ADMIN_PASSWORD")

def safe_error(exc):
    import traceback
    st.error(f"❌ {type(exc).__name__}: {exc}")
    with st.expander("Details"):
        st.code(traceback.format_exc())

def status_pill(s: str) -> str:
    return f'<span class="status-pill status-{s.lower()}">{s.replace("_"," ").title()}</span>'

def sale_pct(orig, sale) -> str:
    try:
        o, s = Decimal(str(orig)), Decimal(str(sale))
        if o > 0 and s < o:
            return f"{int(((o-s)/o)*100)}% OFF"
    except Exception:
        pass
    return ""

def upload_product_media(product_id: str, files: list, existing_media: list | None = None):
    existing_media = existing_media or []
    next_order = max((int(m.get("sort_order") or 0) for m in existing_media), default=-1) + 1
    has_primary_image = any(
        m.get("media_type") == "image" and m.get("is_primary")
        for m in existing_media
    )

    for offset, file in enumerate(files):
        suffix = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else "bin"
        if suffix in IMAGE_SUFFIXES and suffix != "gif":
            try:
                body, suffix = compress_image(file.getvalue(), file.name)
            except Exception:
                body = file.getvalue()
        else:
            body = file.getvalue()

        path = f"{product_id}/{uuid.uuid4().hex}.{suffix}"
        content_type = CONTENT_TYPES.get(suffix, file.type or "application/octet-stream")
        db.storage.from_("product-media").upload(
            path, body, {"content-type": content_type, "upsert": "false"}
        )
        url = db.storage.from_("product-media").get_public_url(path)
        media_type = "video" if suffix in VIDEO_SUFFIXES else "image"
        is_primary = media_type == "image" and not has_primary_image
        db.table("product_media").insert({
            "product_id": product_id,
            "file_path": path,
            "file_url": url,
            "media_type": media_type,
            "caption": file.name,
            "sort_order": next_order + offset,
            "is_primary": is_primary,
        }).execute()
        if is_primary:
            has_primary_image = True


# ─────────────────────────────────────────────────────────────
# Carousel (iframe-based, full JS, no page scroll)
# ─────────────────────────────────────────────────────────────

def carousel_iframe(media_list: list, height: int = 280) -> str:
    images = [m for m in media_list if m.get("media_type") == "image"]
    if not images:
        return ""
    if len(images) == 1:
        url = images[0]["file_url"]
        return (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
                f'<style>*{{margin:0;padding:0;box-sizing:border-box;}}'
                f'body{{background:#f1f5f9;overflow:hidden;}}'
                f'img{{width:100%;height:{height}px;object-fit:cover;display:block;}}'
                f'</style></head><body><img src="{url}" alt="Product"/></body></html>')
    n = len(images)
    imgs_js = "[" + ",".join(f'"{m["file_url"]}"' for m in images) + "]"
    total_h = height + 28  # image + dots row
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#f1f5f9;font-family:sans-serif;overflow:hidden;}}
.wrap{{position:relative;width:100%;height:{height}px;overflow:hidden;}}
.track{{display:flex;height:{height}px;transition:transform .32s cubic-bezier(.4,0,.2,1);}}
.track img{{flex:0 0 100%;width:100%;height:{height}px;object-fit:cover;}}
.btn{{
  position:absolute;top:50%;transform:translateY(-50%);
  background:rgba(255,255,255,.93);border:none;border-radius:50%;
  width:34px;height:34px;font-size:22px;font-weight:700;
  cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.22);
  display:flex;align-items:center;justify-content:center;
  color:#1e293b;z-index:10;padding:0;transition:background .12s,transform .12s;
}}
.btn:hover{{background:#fff;transform:translateY(-50%) scale(1.08);}}
.prev{{left:8px;}}.next{{right:8px;}}
.dots{{
  height:28px;display:flex;align-items:center;justify-content:center;
  gap:7px;background:#fff;
}}
.dot{{
  width:8px;height:8px;border-radius:50%;
  background:rgba(0,0,0,.18);cursor:pointer;
  transition:background .18s,transform .18s;border:none;padding:0;
}}
.dot.on{{background:#2563eb;transform:scale(1.35);}}
.ctr{{
  position:absolute;top:8px;right:10px;
  background:rgba(0,0,0,.46);color:#fff;
  font-size:11px;border-radius:10px;padding:2px 8px;z-index:10;
}}
</style></head><body>
<div class="wrap"><div class="track" id="t"></div>
  <button class="btn prev" id="bp">&#8249;</button>
  <button class="btn next" id="bn">&#8250;</button>
  <div class="ctr" id="c">1/{n}</div>
</div>
<div class="dots" id="d"></div>
<script>
var imgs={imgs_js},idx=0,n={n};
var t=document.getElementById('t'),d=document.getElementById('d'),c=document.getElementById('c');
imgs.forEach(function(src,i){{
  var im=document.createElement('img');im.src=src;im.alt='Photo '+(i+1);t.appendChild(im);
  var dot=document.createElement('button');dot.className='dot'+(i===0?' on':'');
  dot.addEventListener('click',function(e){{e.preventDefault();go(i);}});d.appendChild(dot);
}});
function go(i){{
  idx=((i%n)+n)%n;
  t.style.transform='translateX(-'+(idx*100)+'%)';
  document.querySelectorAll('.dot').forEach(function(el,j){{el.classList.toggle('on',j===idx);}});
  c.textContent=(idx+1)+'/'+n;
}}
document.getElementById('bp').addEventListener('click',function(e){{e.preventDefault();go(idx-1);}});
document.getElementById('bn').addEventListener('click',function(e){{e.preventDefault();go(idx+1);}});
document.addEventListener('keydown',function(e){{if(e.key==='ArrowLeft')go(idx-1);if(e.key==='ArrowRight')go(idx+1);}});
</script></body></html>"""


# ─────────────────────────────────────────────────────────────
# PDF builders (cached)
# ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Preparing cart PDF…", ttl=3600)
def make_cart_pdf_bytes(rows: tuple) -> bytes:
    items = [{"name":r[1],"price":r[2],"quantity":r[3],"description":r[4],"image_url":r[5]} for r in rows]
    total = sum(Decimal(str(r[2]))*r[3] for r in rows if r[2] is not None)
    return build_cart_pdf(items, total)

@st.cache_data(show_spinner="Preparing catalogue PDF…", ttl=3600)
def make_catalogue_pdf_bytes(rows: tuple) -> bytes:
    products = [{"name":r[0],"description":r[1],"price":r[2],"original_price":r[3],"category":r[4],"image_url":r[5]} for r in rows]
    return build_catalogue_pdf(products)


# ─────────────────────────────────────────────────────────────
# Bootstrap DB
# ─────────────────────────────────────────────────────────────

db = get_supabase()
if not db:
    st.title("🛍️ Little Store")
    st.warning("Setup required: add SUPABASE_URL, SUPABASE_KEY and ADMIN_PASSWORD to Streamlit Secrets.")
    st.stop()


# ─────────────────────────────────────────────────────────────
# Store settings (contact info) – stored in session, loaded once
# ─────────────────────────────────────────────────────────────

def load_store_settings() -> dict:
    """Load contact/store info from Supabase store_settings table.
    Returns empty dict silently if the table doesn't exist yet."""
    try:
        res = db.table("store_settings").select("key,value").execute()
        return {r["key"]: r["value"] for r in (res.data or [])}
    except Exception:
        return {}  # table doesn't exist yet – that's fine

def save_store_setting(key: str, value: str):
    try:
        db.table("store_settings").upsert({"key": key, "value": value}).execute()
    except Exception:
        pass

if "store_settings" not in st.session_state:
    st.session_state["store_settings"] = load_store_settings()

settings = st.session_state["store_settings"]

# ─────────────────────────────────────────────────────────────
# Store branding (used in header + hero)
# ─────────────────────────────────────────────────────────────
logo_url   = settings.get("logo_url", "")
store_name = settings.get("store_name") or "Little Store"
cart_count = sum(int(v.get("quantity", 1)) for v in st.session_state.get("cart", {}).values())

# ── Branded header bar ────────────────────────────────────────
logo_tag = (f'<img class="topnav-logo" src="{logo_url}" alt="logo"/>' if logo_url else "🛍️")
st.markdown(f"""
<div class="topnav">
  <div class="topnav-left">{logo_tag}
    <span class="topnav-brand">{store_name}</span>
  </div>
  <span class="topnav-cart">🛒 {cart_count if cart_count else ''} Cart</span>
</div>
""", unsafe_allow_html=True)

# ── Navigation tabs (always visible, always work) ─────────────
tab_shop, tab_order, tab_admin = st.tabs(["🏪 Shop", "📦 My Order", "🔐 Login"])

# ═══════════════════════════════════════════════════════════════
# TAB: SHOP
# ═══════════════════════════════════════════════════════════════
with tab_shop:

    # ── Contact bar ──────────────────────────────────────────
    contact_parts = []
    if settings.get("phone"):
        contact_parts.append(f'📞 <a href="tel:{settings["phone"]}">{settings["phone"]}</a>')
    if settings.get("email"):
        contact_parts.append(f'✉️ <a href="mailto:{settings["email"]}">{settings["email"]}</a>')
    if settings.get("address"):
        contact_parts.append(f'📍 {settings["address"]}')
    if contact_parts:
        st.markdown(
            f'<div class="contact-bar">' + " &nbsp;|&nbsp; ".join(contact_parts) + '</div>',
            unsafe_allow_html=True,
        )

    # ── Hero ─────────────────────────────────────────────────
    store_tagline = settings.get("tagline") or "Discover wireless earbuds, headphones and speakers made for your everyday."
    hero_logo_html = (f'<img class="hero-logo" src="{logo_url}" alt="Store logo"/>'
                      if logo_url else "🛍️")
    st.markdown(f"""
    <div class="hero">
      <div class="hero-inner">
        {hero_logo_html}
        <div>
          <span class="hero-kicker">WIRELESS AUDIO · EVERYDAY ESSENTIALS</span>
          <h1>{store_name}</h1>
          <p>{store_tagline}</p>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Category dropdown ─────────────────────────────────────
    try:
        cat_res = db.table("products").select("category").eq("active", True).execute()
        cat_set = sorted({(r.get("category") or "").strip()
                          for r in (cat_res.data or []) if (r.get("category") or "").strip()})
        all_cats = ["All categories"] + cat_set
    except Exception:
        all_cats = ["All categories"]

    # ── Filter bar ────────────────────────────────────────────
    with st.container(key="store-filters"):
        fc1, fc2, fc3 = st.columns([3, 2, 1])
        with fc1:
            search = st.text_input("Search", placeholder="🔍  Search audio products…",
                                   label_visibility="collapsed")
        with fc2:
            cat_choice = st.selectbox("Category", all_cats, label_visibility="collapsed")
        with fc3:
            sort_opt = st.selectbox("Sort", ["Newest","Price ↑","Price ↓"],
                                    label_visibility="collapsed")

    # ── Fetch + filter ────────────────────────────────────────
    try:
        q = db.table("products").select("id,name,description,price,original_price,category,active").eq("active", True)
        if cat_choice != "All categories":
            q = q.eq("category", cat_choice)
        products = q.execute().data or []
    except Exception:
        # Fallback: original_price column may not exist yet – fetch without it
        try:
            q = db.table("products").select("id,name,description,price,category,active").eq("active", True)
            if cat_choice != "All categories":
                q = q.eq("category", cat_choice)
            products = q.execute().data or []
            for p in products:
                p.setdefault("original_price", None)
        except Exception as e:
            safe_error(e)
            products = []

    # Search + sort (runs regardless of which fetch path was used)
    if search.strip():
        kw = search.strip().lower()
        products = [p for p in products
                    if kw in (p.get("name") or "").lower()
                    or kw in (p.get("description") or "").lower()]
    if sort_opt == "Price ↑":
        products.sort(key=lambda p: float(p.get("price") or 0))
    elif sort_opt == "Price ↓":
        products.sort(key=lambda p: float(p.get("price") or 0), reverse=True)

    if not products:
        st.info("No products found. Try a different search or category.")
    else:
        st.markdown(f'<div class="section-title">Products ({len(products)})</div>',
                    unsafe_allow_html=True)

    cart = st.session_state.setdefault("cart", {})

    # ── Product grid ──────────────────────────────────────────
    # Check if a product detail is being viewed
    detail_pid = st.session_state.get("detail_pid")

    if detail_pid:
        # ── Product detail view ──────────────────────────────
        dp = next((p for p in products if p["id"] == detail_pid), None)
        if dp is None:
            # maybe from a different category; re-fetch
            try:
                dp_res = db.table("products").select("*").eq("id", detail_pid).limit(1).execute().data
                dp = dp_res[0] if dp_res else None
            except Exception:
                dp = None

        if dp:
            if st.button("← Back to products"):
                st.session_state.pop("detail_pid", None)
                st.rerun()

            try:
                dm = (db.table("product_media")
                        .select("id,file_url,media_type,caption,sort_order")
                        .eq("product_id", dp["id"]).order("sort_order").execute().data or [])
            except Exception:
                dm = []

            d_on_sale = (
                dp.get("original_price") is not None and dp.get("price") is not None
                and Decimal(str(dp["original_price"])) > Decimal(str(dp["price"]))
            )
            d_img_count = len([m for m in dm if m.get("media_type") == "image"])

            dc1, dc2 = st.columns([1, 1], gap="large")
            with dc1:
                if d_img_count > 0:
                    car_src = carousel_iframe(dm, height=360)
                    iframe_h = 360 + (28 if d_img_count > 1 else 0)
                    components.html(car_src, height=iframe_h, scrolling=False)
                for m in dm:
                    if m.get("media_type") == "video":
                        st.video(m["file_url"])
            with dc2:
                if dp.get("category"):
                    st.markdown(f'<span class="pc-cat">{dp["category"]}</span>',
                                unsafe_allow_html=True)
                st.markdown(f"## {dp['name']}")
                st.write(dp.get("description") or "")

                if dp.get("price") is not None:
                    if d_on_sale:
                        pct = sale_pct(dp["original_price"], dp["price"])
                        st.markdown(
                            f'<span class="badge-sale">🔥 {pct}</span> '
                            f'<span class="pc-price">{money(dp["price"])}</span> '
                            f'<span class="pc-orig">{money(dp["original_price"])}</span>',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="pc-price">{money(dp["price"])}</span>',
                                    unsafe_allow_html=True)
                else:
                    st.markdown('<span class="pc-contact">📞 Contact for price</span>',
                                unsafe_allow_html=True)

                st.markdown("")
                d_qty = st.number_input("Quantity", min_value=1, max_value=20, value=1, key="detail_qty")
                if st.button("🛒 Add to cart", key="detail_add", type="primary", use_container_width=True):
                    primary_url = next(
                        (m["file_url"] for m in dm if m.get("media_type") == "image"),
                        None
                    )
                    cart[dp["id"]] = {
                        "name":        dp["name"],
                        "price":       float(dp["price"]) if dp.get("price") is not None else None,
                        "quantity":    int(d_qty),
                        "image_url":   primary_url,
                        "description": dp.get("description") or "",
                    }
                    st.toast(f"✅ {dp['name']} added to cart!", icon="🛒")
                    st.session_state.pop("detail_pid", None)
                    st.rerun()
        else:
            st.error("Product not found.")
            if st.button("← Back"):
                st.session_state.pop("detail_pid", None)
                st.rerun()

    else:
        # ── Product grid ─────────────────────────────────────

        # Pre-fetch all media in one query
        all_product_ids = [p["id"] for p in products]
        media_by_product: dict = {pid: [] for pid in all_product_ids}
        try:
            if all_product_ids:
                all_media = (db.table("product_media")
                               .select("product_id,file_url,media_type,is_primary,sort_order")
                               .in_("product_id", all_product_ids)
                               .order("sort_order").execute().data or [])
                for m in all_media:
                    media_by_product[m["product_id"]].append(m)
        except Exception:
            pass

        # Keep each product's image, details, and controls together in one card.

        product_rows = [products[i:i+2] for i in range(0, len(products), 2)]
        for row_index, product_row in enumerate(product_rows):
            with st.container(key=f"product-row-{row_index}"):
                product_cols = st.columns(2, gap="small")
                for col, p in zip(product_cols, product_row):
                    media       = media_by_product.get(p["id"], [])
                    img_list    = [m["file_url"] for m in media if m.get("media_type") == "image"]
                    primary_url = img_list[0] if img_list else None
                    with col.container(border=True):
                        if primary_url:
                            st.image(primary_url, use_container_width=True)
                        else:
                            st.markdown(
                                '<div style="height:120px;background:#f1f5f9;border-radius:8px;'
                                'display:flex;align-items:center;justify-content:center;font-size:1.8rem">'
                                '🛍️</div>',
                                unsafe_allow_html=True,
                            )

                        st.markdown(f"**{p['name']}**")
                        on_sale = (
                            p.get("original_price") is not None and p.get("price") is not None
                            and Decimal(str(p["original_price"])) > Decimal(str(p["price"]))
                        )
                        if p.get("price") is not None:
                            if on_sale:
                                pct = sale_pct(p["original_price"], p["price"])
                                st.markdown(
                                    f'<span class="badge-sale">🔥 {pct}</span> '
                                    f'<span class="pc-price">{money(p["price"])}</span> '
                                    f'<span class="pc-orig">{money(p["original_price"])}</span>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    f'<span class="pc-price">{money(p["price"])}</span>',
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.markdown(
                                '<span class="pc-contact">📞 Contact for price</span>',
                                unsafe_allow_html=True,
                            )

                        qty = st.number_input("Qty", min_value=1, max_value=20, value=1,
                                              key=f"qty_{p['id']}",
                                              label_visibility="collapsed")
                        if st.button("🛒 Add to cart", key=f"add_{p['id']}",
                                     use_container_width=True, type="primary"):
                            cart[p["id"]] = {
                                "name":        p["name"],
                                "price":       float(p["price"]) if p.get("price") is not None else None,
                                "quantity":    int(qty),
                                "image_url":   primary_url,
                                "description": p.get("description") or "",
                            }
                            st.session_state["scroll_to_cart"] = True
                            st.rerun()

                        if st.button("Details", key=f"detail_{p['id']}",
                                     use_container_width=True):
                            st.session_state["detail_pid"] = p["id"]
                            st.rerun()

                        for m in media:
                            if m.get("media_type") == "video":
                                st.video(m["file_url"])

    # ── Cart ─────────────────────────────────────────────────
    st.markdown('<hr class="nice-divider"/>', unsafe_allow_html=True)

    # Auto-scroll to cart when an item was just added
    if st.session_state.pop("scroll_to_cart", False):
        components.html(
            '<script>window.parent.document.getElementById("cart-section")'
            '.scrollIntoView({behavior:"smooth"});</script>',
            height=0,
        )

    st.markdown('<div id="cart-section" class="section-title">🛒 Your Cart</div>',
                unsafe_allow_html=True)

    cart = st.session_state.setdefault("cart", {})
    if not cart:
        st.markdown('<div class="empty-cart">🛍️ Your cart is empty.<br>'
                    '<small>Add some products above.</small></div>',
                    unsafe_allow_html=True)
    else:
        remove_ids = []
        total_val  = Decimal("0")
        for pid, item in list(cart.items()):
            ci1, ci2, ci3, ci4 = st.columns([1, 5, 2, 1])
            with ci1:
                if item.get("image_url"):
                    st.image(item["image_url"], width=60)
                else:
                    st.write("🖼️")
            with ci2:
                price_d = money(item["price"]) if item.get("price") is not None else "Contact for price"
                st.markdown(f"**{item['name']}**")
                st.caption(f"{price_d} each")
            with ci3:
                new_qty = st.number_input("Qty", min_value=1, max_value=20,
                                          value=int(item["quantity"]),
                                          key=f"cart_qty_{pid}",
                                          label_visibility="collapsed")
                item["quantity"] = new_qty
            with ci4:
                if st.button("✖", key=f"remove_{pid}", help="Remove"):
                    remove_ids.append(pid)
            if item.get("price") is not None:
                total_val += Decimal(str(item["price"])) * new_qty

        for pid in remove_ids:
            cart.pop(pid, None)
        if remove_ids:
            st.rerun()

        st.markdown(f"""
        <div class="total-box">
          <p class="total-label">Order total</p>
          <p class="total-amount">{money(total_val)}</p>
        </div>""", unsafe_allow_html=True)
        st.caption("💵 Cash on Delivery · Pay when your order arrives.")

        cart_rows = tuple(sorted(
            (pid, it["name"], it.get("price"), int(it["quantity"]),
             it.get("description") or "", it.get("image_url") or "")
            for pid, it in cart.items()
        ))
        try:
            pdf_bytes = make_cart_pdf_bytes(cart_rows)
            st.download_button("⬇️ Download cart as PDF", data=pdf_bytes,
                               file_name="shopping_cart.pdf", mime="application/pdf",
                               use_container_width=True)
        except Exception as e:
            st.warning("Could not generate cart PDF."); st.caption(str(e))

        st.markdown('<div class="section-title">📋 Checkout</div>', unsafe_allow_html=True)
        with st.form("checkout_form"):
            customer_name = st.text_input("Full name *", max_chars=120, placeholder="Your full name")
            phone_co      = st.text_input("Mobile number *", max_chars=20, placeholder="+91 XXXXX XXXXX")
            address_co    = st.text_area("Delivery address *", max_chars=1000,
                                         placeholder="House / flat, street, city, pin code")
            instructions  = st.text_area("Delivery instructions (optional)", max_chars=500,
                                          placeholder="Gate code, landmark, best time…")
            submitted = st.form_submit_button("✅ Place COD Order", type="primary", use_container_width=True)

        if submitted:
            errors = []
            if len(customer_name.strip()) < 2: errors.append("Enter your full name.")
            digits = "".join(ch for ch in phone_co if ch.isdigit())
            if not (10 <= len(digits) <= 15): errors.append("Enter a valid phone number.")
            if len(address_co.strip()) < 10:   errors.append("Enter a complete delivery address.")
            if not cart: errors.append("Your cart is empty.")
            for err in errors: st.error(err)
            if not errors:
                try:
                    product_ids = list(cart.keys())
                    live = db.table("products").select("id,name,price,active").in_("id", product_ids).execute().data or []
                    live_by_id = {str(p["id"]): p for p in live}
                    if any(not live_by_id.get(str(pid), {}).get("active") for pid in product_ids):
                        st.error("A product is no longer available. Refresh and check your cart.")
                    else:
                        order_items = []; order_total = Decimal("0")
                        for pid, item in cart.items():
                            pr = live_by_id[str(pid)]
                            price = Decimal(str(pr["price"])) if pr["price"] is not None else Decimal("0")
                            qty   = int(item["quantity"]); order_total += price * qty
                            order_items.append({"product_id":pid,"product_name":pr["name"],
                                                "unit_price":float(price),"quantity":qty,"line_total":float(price*qty)})
                        order_code = "COD-" + uuid.uuid4().hex[:10].upper()
                        order = db.table("orders").insert({
                            "order_code":order_code,"customer_name":customer_name.strip(),
                            "phone":phone_co.strip(),"address":address_co.strip(),
                            "instructions":instructions.strip() or None,
                            "total_amount":float(order_total),
                            "payment_method":"COD","payment_status":"pending","status":"pending",
                        }).execute().data
                        order_id = order[0]["id"]
                        for oi in order_items: oi["order_id"] = order_id
                        db.table("order_items").insert(order_items).execute()
                        st.session_state["cart"] = {}
                        st.success("🎉 Order placed!")
                        st.markdown(f"""
                        <div class="order-card">
                          <h3>Order confirmed!</h3>
                          <p>Reference: <code style="font-size:1.1rem">{order_code}</code></p>
                          <p>Total due on delivery: <strong>{money(order_total)}</strong></p>
                          <p style="color:#64748b;font-size:.88rem">Save this reference to track your order.</p>
                        </div>""", unsafe_allow_html=True)
                        st.balloons()
                except Exception as e:
                    safe_error(e)


# ═══════════════════════════════════════════════════════════════
# PAGE: MY ORDER
# ═══════════════════════════════════════════════════════════════

with tab_order:
    st.markdown("""<div class="hero">
        <h1>📦 Track Your Order</h1>
        <p>Enter your order reference and the mobile number you used at checkout.</p>
    </div>""", unsafe_allow_html=True)

    with st.form("order_lookup"):
        code_in  = st.text_input("Order reference", placeholder="COD-XXXXXXXXXX")
        phone_in = st.text_input("Mobile number",   placeholder="+91 XXXXX XXXXX")
        find     = st.form_submit_button("🔍 Find Order", type="primary", use_container_width=True)

    if find:
        if not code_in.strip() or not phone_in.strip():
            st.error("Enter both your order reference and mobile number.")
        else:
            try:
                found = (db.table("orders")
                           .select("order_code,customer_name,total_amount,payment_status,status,created_at")
                           .eq("order_code", code_in.strip().upper())
                           .eq("phone", phone_in.strip())
                           .limit(1).execute().data or [])
                if not found:
                    st.error("Order not found. Check the reference and phone number.")
                else:
                    o = found[0]
                    st.markdown(f"""
                    <div class="order-card">
                      <h3>Order {o['order_code']}</h3>
                      <p>Status: {status_pill(o['status'])}</p>
                      <p>Payment: <strong>Cash on Delivery</strong> · {o['payment_status'].replace('_',' ').title()}</p>
                      <p>Total: <strong>{money(o['total_amount'])}</strong></p>
                      <p style="color:#64748b;font-size:.85rem">Placed: {o.get('created_at','')}</p>
                    </div>""", unsafe_allow_html=True)
            except Exception as e:
                safe_error(e)


# ═══════════════════════════════════════════════════════════════
# PAGE: ADMIN
# ═══════════════════════════════════════════════════════════════

with tab_admin:

    if not st.session_state.get("admin_authenticated"):
        st.markdown("""<div class="hero">
            <h1>🔧 Admin Login</h1>
            <p>Enter your admin password.</p>
        </div>""", unsafe_allow_html=True)
        with st.form("admin_login"):
            pw   = st.text_input("Password", type="password", placeholder="Admin password")
            sign = st.form_submit_button("Sign In", type="primary", use_container_width=True)
        if sign:
            if admin_password() and pw == admin_password():
                st.session_state["admin_authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

    ah1, ah2 = st.columns([5,1])
    with ah1:
        st.markdown("""<div class="hero" style="padding:18px 24px;">
            <h1 style="font-size:1.5rem">🔧 Admin Dashboard</h1>
            <p>Manage products, orders, store settings and download catalogues.</p>
        </div>""", unsafe_allow_html=True)
    with ah2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Log out", use_container_width=True):
            st.session_state["admin_authenticated"] = False; st.rerun()

    # Stats
    try:
        all_p = db.table("products").select("id,active").execute().data or []
        all_o = db.table("orders").select("id,status,total_amount").execute().data or []
        pub   = sum(1 for p in all_p if p.get("active"))
        rev   = sum(float(o.get("total_amount") or 0) for o in all_o if o.get("status") != "cancelled")
        for col, n, lbl in zip(
            st.columns(4),
            [pub, len(all_p)-pub, len(all_o), money(rev)],
            ["Published","Hidden","Orders","Revenue"],
        ):
            col.markdown(f'<div class="admin-stat"><div class="sn">{n}</div><div class="sl">{lbl}</div></div>',
                         unsafe_allow_html=True)
        st.markdown("")
    except Exception:
        pass

    tab_products, tab_orders, tab_settings = st.tabs(["📦 Products", "🧾 Orders", "⚙️ Store Settings"])

    # ══ PRODUCTS ══════════════════════════════════════════════
    with tab_products:

        # Catalogue PDF
        st.markdown('<div class="section-title">📄 Download Catalogue PDF</div>', unsafe_allow_html=True)
        try:
            cat_prods = db.table("products").select("id,name,description,price,original_price,category,active").order("created_at", desc=True).execute().data or []
            if cat_prods:
                rows_list = []
                for cp in cat_prods:
                    try:
                        pm = db.table("product_media").select("file_url,is_primary,media_type,sort_order").eq("product_id",cp["id"]).order("sort_order").execute().data or []
                        img_url = next((m["file_url"] for m in pm if m.get("media_type")=="image" and m.get("is_primary")),
                                       next((m["file_url"] for m in pm if m.get("media_type")=="image"), None))
                    except Exception:
                        img_url = None
                    rows_list.append((cp.get("name",""), cp.get("description","") or "",
                                      cp.get("price"), cp.get("original_price"),
                                      cp.get("category") or "", img_url or ""))
                try:
                    cat_pdf = make_catalogue_pdf_bytes(tuple(rows_list))
                    st.download_button("⬇️ Download Product Catalogue PDF", data=cat_pdf,
                                       file_name="product_catalogue.pdf", mime="application/pdf",
                                       use_container_width=True)
                except Exception as ex:
                    st.warning("Could not generate PDF."); st.caption(str(ex))
        except Exception as e:
            safe_error(e)

        st.markdown('<hr class="nice-divider"/>', unsafe_allow_html=True)

        # Add product
        st.markdown('<div class="section-title">➕ Add New Product</div>', unsafe_allow_html=True)
        with st.form("new_product", clear_on_submit=True):
            np1, np2 = st.columns(2)
            with np1:
                name       = st.text_input("Product name *", max_chars=160)
                category   = st.text_input("Category", placeholder="e.g. Kitchen, Gifts")
                price_text = st.text_input("Price (INR)", placeholder="Leave blank = Contact for price")
                orig_text  = st.text_input("Original price before discount", placeholder="e.g. 799  (leave blank = not on sale)")
            with np2:
                description = st.text_area("Description", max_chars=3000, height=140)
                active      = st.checkbox("Publish immediately", value=True)
                uploads     = st.file_uploader("Photos / videos (up to 8)",
                                               type=["png","jpg","jpeg","webp","gif","mp4","webm","mov"],
                                               accept_multiple_files=True)
            if st.form_submit_button("💾 Save Product", type="primary", use_container_width=True):
                if not name.strip():
                    st.error("Product name required.")
                elif len(uploads or []) > 8:
                    st.error("Max 8 files.")
                else:
                    price_val = orig_val = None
                    ok = True
                    if price_text.strip():
                        try:
                            pv = Decimal(price_text.strip())
                            if not pv.is_finite() or pv < 0: raise InvalidOperation
                            price_val = float(pv)
                        except (InvalidOperation, ValueError):
                            st.error("Invalid price."); ok = False
                    if orig_text.strip() and ok:
                        try:
                            ov = Decimal(orig_text.strip())
                            if not ov.is_finite() or ov < 0: raise InvalidOperation
                            orig_val = float(ov)
                        except (InvalidOperation, ValueError):
                            st.error("Invalid original price."); ok = False
                    if ok:
                        try:
                            ins = db.table("products").insert({
                                "name":name.strip(),"description":description.strip(),
                                "price":price_val,"original_price":orig_val,
                                "category":category.strip() or None,"active":active,
                            }).execute().data
                            pid = ins[0]["id"]
                            upload_product_media(pid, uploads or [])
                            st.success(f"✅ '{name.strip()}' saved.")
                            st.rerun()
                        except Exception as e:
                            safe_error(e)

        st.markdown('<hr class="nice-divider"/>', unsafe_allow_html=True)

        # Existing products
        st.markdown('<div class="section-title">📋 Existing Products</div>', unsafe_allow_html=True)
        try:
            prods = db.table("products").select("*").order("created_at",desc=True).execute().data or []
            if not prods: st.info("No products yet.")
            for p in prods:
                lbl = f"{p['name']} · {money(p.get('price'))} · {'✅ Published' if p['active'] else '🔒 Hidden'}"
                with st.expander(lbl):
                    try:
                        med = (db.table("product_media").select("*")
                               .eq("product_id", p["id"]).order("sort_order")
                               .execute().data or [])
                    except Exception as e:
                        safe_error(e)
                        med = []

                    media_revision_key = f"edit_media_revision_{p['id']}"
                    media_revision = st.session_state.get(media_revision_key, 0)
                    with st.form(f"edit_{p['id']}"):
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            ename  = st.text_input("Name",     value=p["name"])
                            ecat   = st.text_input("Category", value=p.get("category") or "")
                            eprice = st.text_input("Price (blank=Contact)", value=str(p["price"]) if p.get("price") is not None else "")
                            eorig  = st.text_input("Original price (blank=not on sale)", value=str(p["original_price"]) if p.get("original_price") is not None else "")
                        with ec2:
                            edesc  = st.text_area("Description", value=p.get("description") or "", height=110)
                            eact   = st.checkbox("Published", value=bool(p["active"]))
                            edit_uploads = st.file_uploader(
                                "Add photos / videos (up to 8 total)",
                                type=["png","jpg","jpeg","webp","gif","mp4","webm","mov"],
                                accept_multiple_files=True,
                                key=f"edit_media_{p['id']}_{media_revision}",
                                help="Existing media stays in place. Remove old files below if you want to replace them.",
                            )
                        if st.form_submit_button("💾 Update"):
                            validation_error = None
                            if not ename.strip():
                                validation_error = "Product name required."
                            elif len(med) + len(edit_uploads or []) > 8:
                                remaining = max(0, 8 - len(med))
                                validation_error = (
                                    f"This product already has {len(med)} media file(s). "
                                    f"You can add at most {remaining} more."
                                )
                            if validation_error:
                                st.error(validation_error)
                            else:
                                try:
                                    epv = None
                                    if eprice.strip():
                                        ev = Decimal(eprice.strip())
                                        if not ev.is_finite() or ev < 0: raise InvalidOperation
                                        epv = float(ev)
                                    eov = None
                                    if eorig.strip():
                                        ov2 = Decimal(eorig.strip())
                                        if not ov2.is_finite() or ov2 < 0: raise InvalidOperation
                                        eov = float(ov2)
                                    db.table("products").update({
                                        "name":ename.strip(),"description":edesc.strip(),
                                        "price":epv,"original_price":eov,
                                        "category":ecat.strip() or None,"active":eact,
                                    }).eq("id",p["id"]).execute()
                                    upload_product_media(p["id"], edit_uploads or [], med)
                                    if edit_uploads:
                                        st.session_state[media_revision_key] = media_revision + 1
                                    st.success("Updated."); st.rerun()
                                except Exception as e: safe_error(e)

                    # Media grid
                    if med:
                        st.markdown("**Media**")
                        mcols = st.columns(min(len(med),4))
                        for mi, m in enumerate(med):
                            with mcols[mi%4]:
                                if m["media_type"]=="video": st.video(m["file_url"])
                                else: st.image(m["file_url"], use_container_width=True)
                                st.caption(m.get("caption") or "")
                                if st.button("🗑 Delete", key=f"delmedia_{m['id']}"):
                                    try:
                                        db.storage.from_("product-media").remove([m["file_path"]])
                                        db.table("product_media").delete().eq("id",m["id"]).execute()
                                        st.rerun()
                                    except Exception as e: safe_error(e)

                    st.markdown("---")
                    if st.button("🗑 DELETE PRODUCT", key=f"del_{p['id']}"):
                        st.session_state["confirm_delete"] = p["id"]
                    if st.session_state.get("confirm_delete") == p["id"]:
                        st.warning("⚠️ Permanent — deletes product and all media.")
                        if st.button("⚠️ Confirm", key=f"conf_{p['id']}"):
                            try:
                                med2 = db.table("product_media").select("id,file_path").eq("product_id",p["id"]).execute().data or []
                                pths = [m["file_path"] for m in med2]
                                if pths: db.storage.from_("product-media").remove(pths)
                                db.table("products").delete().eq("id",p["id"]).execute()
                                st.session_state.pop("confirm_delete",None)
                                st.rerun()
                            except Exception as e: safe_error(e)
        except Exception as e: safe_error(e)

    # ══ ORDERS ════════════════════════════════════════════════
    with tab_orders:
        st.markdown('<div class="section-title">🧾 Customer Orders</div>', unsafe_allow_html=True)
        oc1, oc2 = st.columns([2,1])
        with oc1:
            order_search = st.text_input("Search reference / name / phone",
                                         label_visibility="collapsed", placeholder="Search…")
        with oc2:
            sf = st.selectbox("Status",
                              ["All","pending","confirmed","processing","shipped","delivered","cancelled"],
                              label_visibility="collapsed")
        try:
            orders = db.table("orders").select("*").order("created_at",desc=True).limit(300).execute().data or []
            if sf != "All": orders = [o for o in orders if o["status"]==sf]
            if order_search.strip():
                kw = order_search.strip().lower()
                orders = [o for o in orders if kw in (o.get("order_code") or "").lower()
                          or kw in (o.get("customer_name") or "").lower()
                          or kw in (o.get("phone") or "").lower()]
            if not orders: st.info("No orders match the filter.")
            for o in orders:
                lbl = f"{o['order_code']} · {o['customer_name']} · {money(o['total_amount'])} · {o['status'].replace('_',' ').title()}"
                with st.expander(lbl):
                    oi1, oi2 = st.columns(2)
                    with oi1:
                        st.markdown(f"**Phone:** {o['phone']}")
                        st.markdown(f"**Address:** {o['address']}")
                        if o.get("instructions"): st.markdown(f"**Instructions:** {o['instructions']}")
                        st.markdown(f"**Placed:** {o.get('created_at','')}")
                    with oi2:
                        st.markdown(f"**Status:** {status_pill(o['status'])}", unsafe_allow_html=True)
                        st.markdown(f"**Payment:** COD · {o['payment_status'].replace('_',' ').title()}")
                        st.markdown(f"**Total:** {money(o['total_amount'])}")
                    try:
                        oid = db.table("order_items").select("*").eq("order_id",o["id"]).execute().data or []
                        if oid:
                            st.table([{"Product":i["product_name"],"Qty":i["quantity"],
                                       "Unit price":money(i["unit_price"]),"Line total":money(i["line_total"])} for i in oid])
                    except Exception: st.warning("Could not load order items.")
                    with st.form(f"oupd_{o['id']}"):
                        slist = ["pending","confirmed","processing","shipped","delivered","cancelled"]
                        plist = ["pending","paid","not_collected"]
                        u1,u2 = st.columns(2)
                        with u1: ns = st.selectbox("Order status", slist, index=slist.index(o["status"] if o["status"] in slist else "pending"))
                        with u2: np2 = st.selectbox("Payment status", plist, index=plist.index(o["payment_status"] if o["payment_status"] in plist else "pending"))
                        if st.form_submit_button("💾 Update Order"):
                            try:
                                db.table("orders").update({"status":ns,"payment_status":np2}).eq("id",o["id"]).execute()
                                st.success("Updated."); st.rerun()
                            except Exception as e: safe_error(e)
        except Exception as e: safe_error(e)

    # ══ STORE SETTINGS ════════════════════════════════════════
    with tab_settings:
        st.markdown('<div class="section-title">⚙️ Store Contact & Info</div>', unsafe_allow_html=True)
        st.caption("These details appear on the Shop page so customers can contact you.")

        # Show current logo if set
        if settings.get("logo_url"):
            lc1, lc2 = st.columns([1,4])
            with lc1:
                st.image(settings["logo_url"], width=80)
            with lc2:
                st.caption("Current logo · Upload a new one below to replace it.")

        # Logo upload (outside the form so we can handle it separately)
        logo_file = st.file_uploader(
            "Upload store logo (PNG / JPG / WEBP, optional)",
            type=["png","jpg","jpeg","webp"],
            key="logo_upload",
        )
        if logo_file:
            try:
                from store_utils import compress_image as _ci
                logo_bytes, logo_ext = _ci(logo_file.getvalue(), logo_file.name)
                logo_path = f"logos/logo.{logo_ext}"
                ct = CONTENT_TYPES.get(logo_ext, "image/jpeg")
                # Try to remove old logo first (ignore errors)
                try: db.storage.from_("product-media").remove([logo_path])
                except Exception: pass
                db.storage.from_("product-media").upload(
                    logo_path, logo_bytes, {"content-type": ct, "upsert": "true"}
                )
                logo_pub_url = db.storage.from_("product-media").get_public_url(logo_path)
                save_store_setting("logo_url", logo_pub_url)
                st.session_state["store_settings"]["logo_url"] = logo_pub_url
                st.success("Logo uploaded!")
                st.rerun()
            except Exception as e:
                st.warning("Could not upload logo.")
                st.caption(str(e))

        if settings.get("logo_url"):
            if st.button("🗑 Remove logo"):
                try:
                    db.storage.from_("product-media").remove(["logos/logo.png","logos/logo.jpg","logos/logo.webp","logos/logo.jpeg"])
                except Exception: pass
                save_store_setting("logo_url", "")
                st.session_state["store_settings"]["logo_url"] = ""
                st.rerun()

        st.markdown("---")

        with st.form("store_settings_form"):
            s_name    = st.text_input("Store name",        value=settings.get("store_name","Little Store"))
            s_tagline = st.text_input("Tagline",            value=settings.get("tagline","Browse our collection · Place your order · Pay on delivery"))
            s_phone   = st.text_input("Phone / WhatsApp",  value=settings.get("phone",""),   placeholder="+91 XXXXX XXXXX")
            s_email   = st.text_input("Email",             value=settings.get("email",""),   placeholder="store@example.com")
            s_address = st.text_input("Address",           value=settings.get("address",""), placeholder="123, Street, City")
            if st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True):
                try:
                    for k, v in [("store_name",s_name),("tagline",s_tagline),
                                  ("phone",s_phone),("email",s_email),("address",s_address)]:
                        save_store_setting(k, v)
                    st.session_state["store_settings"].update({
                        "store_name":s_name,"tagline":s_tagline,
                        "phone":s_phone,"email":s_email,"address":s_address,
                    })
                    st.success("Settings saved!")
                    st.rerun()
                except Exception as e:
                    st.warning("Could not save. Make sure the store_settings table exists.")
                    st.caption(str(e))

        with st.expander("📋 SQL to create store_settings table (run once in Supabase SQL Editor)"):
            st.code("""
create table if not exists public.store_settings (
  key   text primary key,
  value text not null default ''
);
alter table public.store_settings enable row level security;
-- Allow server-side reads (service role key bypasses RLS)
-- Public can read store info
create policy "Public read store settings" on public.store_settings
  for select to anon, authenticated using (true);
""", language="sql")
