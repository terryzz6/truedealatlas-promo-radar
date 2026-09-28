# ILANG: ROLE=builder; READ=.ilang/site.ilang + data/offers.json; OUTPUT=site/; NEVER=fake prices
from __future__ import annotations
import html, json, re, shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from scraper import parse_config, PROMO_CODE

ROOT=Path(__file__).parent; DATA=ROOT/"data"/"offers.json"; SITE=ROOT/"site"; BASE="https://"+parse_config()["meta"].get("domain","truedealatlas.com").strip().rstrip("/")
def esc(v): return html.escape(str(v), quote=True)
def slug(v):
    value = re.sub(r"[^a-z0-9]+", "-", v.lower()).strip("-") or "item"
    return value[: 95].rstrip("-")
def load_data():
    cfg=parse_config(); payload=json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"offers":[],"providers":[],"generated_at":datetime.now(timezone.utc).isoformat()}
    articles_path=ROOT/"data"/"articles.json"
    payload["articles"]=(json.loads(articles_path.read_text(encoding="utf-8")).get("articles",[]) if articles_path.exists() else [])
    payload.setdefault("brand",cfg["meta"].get("brand","TrueDealAtlas")); payload.setdefault("niche",cfg["meta"].get("niche","US consumer brand coupons and discounts")); return cfg,payload
def load_brand_coupon_pages():
    path=ROOT/"data"/"brand_coupon_pages.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
def jsonld(obj): return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False)+'</script>'
def format_checked(value):
    try:
        checked=datetime.fromisoformat(value.replace("Z","+00:00"))
        return "Source checked {} {}, {}".format(checked.strftime("%b"),checked.day,checked.year)
    except (AttributeError, TypeError, ValueError):
        return "Check date unavailable"

def icon(name):
    return '<svg class="icon" aria-hidden="true" width="20" height="20"><use href="/assets/icons.svg#{}"></use></svg>'.format(esc(name))

def store_mark(name):
    image=next((ROOT/"templates"/"store-icons").glob(slug(name)+".*"),None)
    if image:
        return '<span class="store-mark"><img src="/assets/stores/{}" alt="" width="32" height="32" loading="lazy"></span>'.format(esc(image.name))
    return '<span class="store-mark initials" aria-hidden="true">{}</span>'.format(esc(name[:2].upper()))

def coupon_code(offer):
    text=str(offer.get("offer_text", ""))
    match=PROMO_CODE.search(text)
    return match.group(1) if match else ""

def offer_kind(offer):
    if coupon_code(offer):
        return "codes"
    if re.search(r"\bfree shipping\b", str(offer.get("offer_text", "")), re.I):
        return "shipping"
    return "sales"

def offer_saving(offer):
    text=str(offer.get("offer_text", ""))
    percent=offer.get("discount_percent")
    if percent:
        prefix="BOGO " if re.search(r"\bBOGO\b|buy one.{0,30}get one", text, re.I) else "Up to " if re.search(r"\bup to\b", text, re.I) else "Extra " if re.search(r"\bextra\b", text, re.I) else ""
        return "{}{}% off".format(prefix, percent)
    amount=re.search(r"\$\s*([\d,]+(?:\.\d{2})?)\s*off\b", text, re.I)
    if amount:
        return "$"+amount.group(1)+" off"
    if offer_kind(offer)=="shipping":
        return "Free shipping"
    if re.search(r"\bfree gift\b", text, re.I):
        return "Free gift"
    return "Store offer"

def copy_control(offer):
    code=coupon_code(offer)
    if not code:
        return ""
    return '<div class="coupon-code"><span>Promo code <strong>{}</strong></span><button class="icon-button copy-code" type="button" data-code="{}" aria-label="Copy promo code {}" title="Copy promo code">{}</button></div>'.format(esc(code),esc(code),esc(code),icon("copy"))

def offer_filters(offers):
    stores=sorted({o["provider"] for o in offers},key=str.lower)
    options="".join('<option value="{}">{}</option>'.format(esc(name),esc(name)) for name in stores)
    tabs="".join('<button type="button" role="tab" id="tab-{}" aria-controls="deal-grid" aria-selected="{}" tabindex="{}" data-kind="{}">{}</button>'.format(key,"true" if key=="all" else "false","0" if key=="all" else "-1",key,label) for key,label in (("all","All offers"),("codes","Promo codes"),("sales","Deals"),("shipping","Free shipping")))
    return '<div class="offer-tabs" role="tablist" aria-label="Offer type">{}</div><div class="filter-bar"><div class="filter-fields"><label>Store<select id="store-filter"><option value="">All stores</option>{}</select></label><label>Sort by<select id="sort-order"><option value="featured">Store name</option><option value="discount">Highest % off</option><option value="newest">Recently checked</option></select></label></div><label class="saved-filter"><input type="checkbox" id="saved-only"> Saved offers</label><button class="text-button" id="reset-filters" type="button" hidden>Clear filters {}</button></div>'.format(tabs,options,icon("x"))
def display_offer_title(offer):
    title=str(offer.get("title", ""))
    prefix=str(offer.get("provider", ""))+":"
    return title[len(prefix):].strip() if title.lower().startswith(prefix.lower()) else title
def page(title,desc,body,path="/",template_name=None,footer_brand=None):
    canonical=BASE+("/" if path=="/" else path)
    if template_name:
        template_path=ROOT/"templates"/template_name
        if template_path.exists():
            body=template_path.read_text(encoding="utf-8").replace("{{content}}",body)
    nav="".join('<a href="{}"{}>{}</a>'.format(url,' aria-current="page"' if (path==url or url!="/" and path.startswith(url)) else "",label) for url,label in (("/","Coupons & deals"),("/providers/","Stores"),("/compare.html","Compare"),("/guides/","Guides")))
    search='<form class="header-search" id="deal-search-form" action="/" role="search"><label class="sr-only" for="deal-search">Search stores, coupons, and deals</label>{}<input id="deal-search" name="q" type="search" placeholder="Search stores, coupons & deals" autocomplete="off"><button class="icon-button" type="submit" aria-label="Search" title="Search">{}</button></form>'.format(icon("search"),icon("arrow-right"))
    markup='<!doctype html><html lang="en-US"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{}</title><meta name="description" content="{}"><meta name=\'impact-site-verification\' value=\'e0b16352-9ce9-435f-9d55-19b31ccd938b\'><link rel="canonical" href="{}"><meta property="og:title" content="{}"><meta property="og:description" content="{}"><meta property="og:url" content="{}"><meta name="twitter:card" content="summary"><link rel="stylesheet" href="/styles.css"><script src="/site.js" defer></script></head><body><a class="skip-link" href="#main">Skip to content</a><div class="trust-strip">Offers from official store pages. Terms apply.</div><header class="site-header"><div class="header-inner"><a class="brand" href="/" aria-label="TrueDealAtlas home"><span class="brand-mark" aria-hidden="true">{}</span><span>TrueDealAtlas</span></a>{}<a class="saved-link" href="/?saved=1">{}<span>Saved <span data-saved-count>0</span></span></a><details class="mobile-nav"><summary aria-label="Open navigation" title="Menu">{}</summary><nav aria-label="Mobile navigation">{}</nav></details></div><nav class="desktop-nav" aria-label="Primary navigation">{}</nav></header><main id="main">{}</main><div class="toast" id="site-toast" role="status" aria-live="polite" hidden></div><footer><div><a class="footer-brand" href="/">TrueDealAtlas</a><p>Independent coupons and deals from official US store pages. Offers can change; confirm availability and terms at the store.</p></div><nav aria-label="Footer navigation"><a href="/about.html">About</a><a href="/privacy.html">Privacy</a><a href="/contact.html">Contact</a><a href="/.ilang/site.ilang">Source policy</a></nav></footer></body></html>'.format(esc(title),esc(desc),esc(canonical),esc(title),esc(desc),esc(canonical),icon("tag"),search,icon("heart"),icon("menu"),nav,nav,body)
    if footer_brand:
        note='<p class="brand-copyright">&copy; {} TrueDealAtlas. {} page.</p>'.format(datetime.now(timezone.utc).year,esc(footer_brand))
        markup=markup.replace('</p></div><nav aria-label="Footer navigation">','</p>'+note+'</div><nav aria-label="Footer navigation">',1)
    return markup
def offer_card(o):
    detail="/deals/{}-{}.html".format(slug(o["provider"]),slug(o["title"]))
    search_text="{} {} {} {}".format(o.get("provider",""),o.get("title",""),o.get("offer_text",""),o.get("conditions", "")).lower()
    kind=offer_kind(o); label={"codes":"Promo code","shipping":"Shipping offer","sales":"Deal"}[kind]
    terms=o.get("offer_text") or o.get("conditions") or "See store for terms."
    return '<article class="deal deal-card" data-search="{}" data-store="{}" data-kind="{}" data-discount="{}" data-checked="{}" data-id="{}"><div class="deal-top"><a class="merchant" href="/providers/{}.html">{}<span>{}</span></a><button class="icon-button save-offer" type="button" data-id="{}" aria-pressed="false" aria-label="Save {} offer: {}" title="Save offer">{}</button></div><div class="deal-body"><span class="saving">{}</span><span class="offer-type {}">{}</span><h3><a href="{}">{}</a></h3><p class="conditions">{}</p>{}</div><div class="deal-footer"><a class="button" href="{}" target="_blank" rel="nofollow noopener">Get deal {}<span class="sr-only"> at {} (opens in a new tab)</span></a><a class="details-link" href="{}">Offer details</a></div><p class="checked">{}</p></article>'.format(esc(search_text),esc(o["provider"]),kind,esc(o.get("discount_percent",0)),esc(o.get("fetched_at","")),esc(detail),slug(o["provider"]),store_mark(o["provider"]),esc(o["provider"]),esc(detail),esc(o["provider"]),esc(display_offer_title(o)),icon("heart"),esc(offer_saving(o)),kind,label,detail,esc(display_offer_title(o)),esc(terms),copy_control(o),esc(o["offer_url"]),icon("arrow-up-right"),esc(o["provider"]),detail,esc(format_checked(o.get("fetched_at",""))))
def provider_result_message(provider, has_offers):
    result=provider.get("result")
    if result=="unavailable" or (not result and provider.get("status")=="error"):
        return "Source not retrieved in this update. Previously verified offers remain listed with their original check times."
    if not has_offers and (result=="empty" or provider.get("status")=="ok"):
        return "The source was retrieved successfully, but no active offer text was detected in this update."
    return ""
def article_card(article):
    path="/guides/{}.html".format(slug(article["slug"]))
    return '<article class="deal"><span class="tag">Guide</span><h3><a href="{}">{}</a></h3><p>{}</p><a class="button" href="{}">Read the guide</a></article>'.format(path,esc(article["title"]),esc(article.get("description","")),path)

def brand_coupon_content(item):
    brand=esc(item["brand"])
    rows="".join('<tr><td>{}</td><td>{}</td><td><a href="{}" rel="nofollow noopener" target="_blank" aria-label="Official {} page (opens in a new tab)">Official {} page</a></td><td>{}</td></tr>'.format(esc(o["offer"]),esc(o["condition"]),esc(o["source"]),brand,brand,esc(o["checked"])) for o in item["offers"])
    faq="".join('<section><h3>{}</h3><p>{}</p></section>'.format(esc(q["question"]),esc(q["answer"])) for q in item["faq"])
    schema={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q["question"],"acceptedAnswer":{"@type":"Answer","text":q["answer"]}} for q in item["faq"]]}
    return '<article class="detail"><p class="eyebrow">Official {} offers</p><h1>{}</h1><p class="answer"><strong>Answer:</strong> {}</p><p class="source-note">Offers can change. Confirm the displayed terms on the official site before purchasing.</p><h2>Offers and eligibility</h2><div class="table-wrap" role="region" aria-label="{} official offers" tabindex="0"><table><thead><tr><th scope="col">Offer</th><th scope="col">How to get it</th><th scope="col">Official source</th><th scope="col">Checked</th></tr></thead><tbody>{}</tbody></table></div><h2>Frequently asked questions</h2>{}{}</article>'.format(brand,esc(item["title"]),esc(item["answer"]),brand,rows,faq,jsonld(schema))

def offer_list(offers, heading="Browse offers"):
    cards="".join(offer_card(o) for o in offers) or '<p class="empty static-empty">No offers currently listed. Check the official store for current availability.</p>'
    return '<section class="deals-section" aria-labelledby="offers-heading"><div class="section-head"><h2 id="offers-heading">{}</h2><span class="result-count" id="deal-result-count" role="status" aria-live="polite">{} offers</span></div>{}<div class="grid deal-grid" id="deal-grid" role="tabpanel" aria-labelledby="tab-all">{}</div><div class="empty search-empty" id="search-empty" hidden><h3>No offers found</h3><p id="empty-message">Try another store or search term.</p><button class="button" type="button" id="empty-reset">Clear filters</button></div><div class="load-more-wrap"><button class="load-more" id="load-more" type="button" hidden>Show more offers {}</button></div></section>'.format(esc(heading),len(offers),offer_filters(offers),cards,icon("chevron-down"))

def home_content(data, offers, store_links, guide_section):
    stores=len({o["provider"] for o in offers})
    try:
        updated=datetime.fromisoformat(data["generated_at"].replace("Z","+00:00"))
        update_label=updated.strftime("%b ")+str(updated.day)+", "+str(updated.year)
    except (KeyError, ValueError):
        update_label="Date unavailable"
    return '<section class="browse-intro"><h1>Coupons & deals</h1><p>Official offers from US stores and brands.</p><div class="index-summary"><span><strong>{}</strong> offers</span><span><strong>{}</strong> stores with offers</span><span>Index updated {}</span></div></section><section class="store-section" aria-labelledby="stores-heading"><div class="section-head"><h2 id="stores-heading">Explore stores</h2><a class="text-link" href="/providers/">All stores {}</a></div><div class="store-strip">{}</div></section>{}{}<section class="source-coverage"><div>{}<h2>From the store. With the terms.</h2></div><p>Every offer links to its official source. Source checks confirm the published offer text; availability and eligibility are determined by the store.</p><a class="text-link" href="/about.html">About our sources {}</a></section>'.format(len(offers),stores,esc(update_label),icon("arrow-right"),store_links,offer_list(offers),guide_section,icon("external-link"),icon("arrow-right"))

def write_assets():
    assets=SITE/"assets"; assets.mkdir(exist_ok=True)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    sprite=ET.Element("{http://www.w3.org/2000/svg}svg")
    for source in sorted((ROOT/"templates"/"icons").glob("*.svg")):
        svg=ET.parse(source).getroot()
        symbol=ET.SubElement(sprite,"{http://www.w3.org/2000/svg}symbol",{"id":source.stem,"viewBox":svg.get("viewBox","0 0 24 24"),"fill":"none","stroke":"currentColor","stroke-width":"2","stroke-linecap":"round","stroke-linejoin":"round"})
        symbol.extend(list(svg))
    ET.ElementTree(sprite).write(assets/"icons.svg",encoding="utf-8",xml_declaration=True)
    license_path=ROOT/"templates"/"icons"/"LICENSE"
    if license_path.exists():
        shutil.copyfile(license_path,assets/"lucide-LICENSE.txt")
    images=ROOT/"templates"/"store-icons"
    if images.exists():
        shutil.copytree(images,assets/"stores",dirs_exist_ok=True)
def build():
    cfg,data=load_data(); brand_pages=load_brand_coupon_pages(); SITE.mkdir(exist_ok=True); (SITE/"providers").mkdir(exist_ok=True); (SITE/"deals").mkdir(exist_ok=True)
    for old_deal in (SITE/"deals").glob("*.html"):
        old_deal.unlink()
    (SITE/"styles.css").write_text(STYLES,encoding="utf-8")
    (SITE/"site.js").write_text(SITE_JS,encoding="utf-8")
    write_assets()
    offers=sorted([o for o in data.get("offers",[]) if o.get("active",True)],key=lambda o:(o["provider"].lower(),display_offer_title(o).lower()))
    paths=["{}-{}".format(slug(o["provider"]),slug(o["title"])) for o in offers]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate deal paths detected; scraper titles must be unique")
    articles=data.get("articles",[])
    guide_cards="".join(article_card(a) for a in articles[:6])
    guide_section='<section class="guides-section"><div class="section-head"><h2>Shopping guides</h2><a class="text-link" href="/guides/">All guides {}</a></div><div class="grid">{}</div></section>'.format(icon("arrow-right"),guide_cards) if guide_cards else ""
    provider_counts={}
    for offer in offers:
        provider_counts[offer["provider"]]=provider_counts.get(offer["provider"],0)+1
    popular=sorted(provider_counts,key=lambda name:(-provider_counts[name],name.lower()))[:8]
    store_links="".join('<a href="/providers/{}.html">{}<span><strong>{}</strong><small>{} offers</small></span></a>'.format(slug(name),store_mark(name),esc(name),provider_counts[name]) for name in popular)
    body=home_content(data,offers,store_links,guide_section)
    (SITE/"index.html").write_text(page("TrueDealAtlas | Official US Deals","A transparent index of official US consumer brand offers and sale pages.",body,template_name="index.html"),encoding="utf-8")
    about_body='''<article class="detail"><p class="eyebrow">About TrueDealAtlas</p><h1>About TrueDealAtlas</h1><p>TrueDealAtlas is an independent index of public sale pages and promotions from US consumer brands.</p><h2>Where the data comes from</h2><p>Every listing begins with a public, official brand source such as a sale page, sitemap, or feed. We do not invent offers, prices, expiration dates, or commission claims. When a source does not expose a reliable detail, we leave it out.</p><p>The public dataset is archived on <a href="https://doi.org/10.5281/zenodo.22885986">Zenodo (DOI: 10.5281/zenodo.22885986)</a>.</p><h2>How often sources are checked</h2><p>Our deterministic Python update pipeline checks configured official sources every six hours and rebuilds the static site from the results.</p><h2>Who maintains the site</h2><p>TrueDealAtlas is maintained by its owner with an automated, source-traceable publishing workflow. Questions and corrections are welcome through the <a href="/contact.html">contact page</a>.</p><p><a href="/privacy.html">Privacy</a> · <a href="/contact.html">Contact</a></p></article>'''
    privacy_body='''<article class="detail"><p class="eyebrow">Site policy</p><h1>Privacy Policy</h1><p>Last updated: September 16, 2026.</p><h2>Information we do not collect</h2><p>TrueDealAtlas does not offer user accounts, accept payments, or use a contact form. We do not intentionally collect names, postal addresses, payment details, or other personal information through this site.</p><h2>Hosting and measurement</h2><p>The site does not currently load a separate analytics service or advertising tracker. Cloudflare hosts and delivers the site and may process basic request and security data under its own policies.</p><h2>Outbound and affiliate links</h2><p>Links can take you to official third-party websites, which have their own privacy practices. TrueDealAtlas may use affiliate links. When a link is an affiliate link, it will be disclosed clearly; a qualifying purchase may earn the site a commission at no additional cost to you.</p><h2>Questions</h2><p>For privacy questions, use the <a href="/contact.html">contact page</a>.</p><p><a href="/about.html">About</a> · <a href="/contact.html">Contact</a></p></article>'''
    contact_body='''<article class="detail"><p class="eyebrow">Get in touch</p><h1>Contact TrueDealAtlas</h1><p>Email <a href="mailto:contact@truedealatlas.com">contact@truedealatlas.com</a>. We aim to reply within three business days.</p><p><a href="/about.html">About</a> · <a href="/privacy.html">Privacy</a></p></article>'''
    (SITE/"about.html").write_text(page("About TrueDealAtlas","How TrueDealAtlas sources and checks official US brand offers.",about_body,"/about.html"),encoding="utf-8")
    (SITE/"privacy.html").write_text(page("Privacy Policy | TrueDealAtlas","Privacy, hosting, analytics, and affiliate disclosure for TrueDealAtlas.",privacy_body,"/privacy.html"),encoding="utf-8")
    (SITE/"contact.html").write_text(page("Contact TrueDealAtlas","How to contact TrueDealAtlas about corrections and questions.",contact_body,"/contact.html"),encoding="utf-8")
    not_found=page("Page Not Found | TrueDealAtlas","The requested page does not exist.",'<article class="detail"><p class="eyebrow">404</p><h1>Page not found</h1><p>This offer may have expired or been removed after verification.</p><a href="/">Browse current deals</a></article>',"/404.html").replace('<meta name="description"','<meta name="robots" content="noindex"><meta name="description"',1)
    (SITE/"404.html").write_text(not_found,encoding="utf-8")
    links=[]
    for p in data.get("providers",[]):
        ps=slug(p["name"]); po=[o for o in offers if o.get("provider")==p["name"]]; status_message=provider_result_message(p,bool(po))
        status_note='<p class="source-note">{}</p>'.format(esc(status_message)) if status_message else ""
        pbody='<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Coupons & deals</a><span>/</span><a href="/providers/">Stores</a><span>/</span><span>{}</span></nav><section class="hero compact"><p class="eyebrow">Official store offers</p><h1>{} coupons & deals</h1><p>{} offers from the official store source.</p><a class="button secondary" href="{}" target="_blank" rel="nofollow noopener">Visit {} {}<span class="sr-only"> (opens in a new tab)</span></a>{}</section>{}'.format(esc(p["name"]),esc(p["name"]),len(po),esc(p["source_url"]),esc(p["name"]),icon("arrow-up-right"),status_note,offer_list(po, "{} offers".format(p["name"])))
        if po:
            prices=[float(o["price"]) for o in po if o.get("price")]
            p_schema={"@context":"https://schema.org","@type":"Product","name":p["name"],"url":BASE+"/providers/"+ps+".html","offers":{"@type":"AggregateOffer","offerCount":len(po)}}
            if prices:
                p_schema["offers"].update({"lowPrice":min(prices),"highPrice":max(prices),"priceCurrency":"USD"})
            pbody += jsonld(p_schema)
        (SITE/"providers"/(ps+".html")).write_text(page(p["name"]+" Coupons & Deals | TrueDealAtlas","Official {} sale and promotion source status.".format(p["name"]),pbody,"/providers/"+ps+".html","provider.html"),encoding="utf-8")
        note="{} offers".format(len(po)) if po else "No offers listed"
        if p.get("status")=="error":
            note += " / Source unavailable"
        links.append('<li data-store-name="{}"><a href="/providers/{}.html">{}<span><strong>{}</strong><small>{}</small></span>{}</a></li>'.format(esc(p["name"].lower()),ps,store_mark(p["name"]),esc(p["name"]),esc(note),icon("arrow-right")))
    links.sort()
    directory='<section class="hero compact"><p class="eyebrow">Shop by store</p><h1>Stores & brands</h1><p>Browse official coupons, sales, and shipping offers.</p></section><div class="directory-toolbar"><label for="store-search" class="sr-only">Find a store</label><div class="directory-search">{}<input type="search" id="store-search" placeholder="Find a store" autocomplete="off"></div><span id="store-result-count" role="status">{} stores</span></div><ul class="store-directory">{}</ul><div id="store-empty" class="empty" hidden>No stores match your search.</div>'.format(icon("search"),len(links),"".join(links))
    (SITE/"providers"/"index.html").write_text(page("Stores & Brands | TrueDealAtlas","Browse US store coupons and deals from official sources",directory,"/providers/","provider.html"),encoding="utf-8")
    rows="".join('<tr class="compare-row" data-discount="{}" data-checked="{}"><td><a href="/providers/{}.html">{}</a></td><td><a href="/deals/{}-{}.html">{}</a></td><td>{}</td><td>{}</td></tr>'.format(o.get("discount_percent",0),esc(o.get("fetched_at","")),slug(o["provider"]),esc(o["provider"]),slug(o["provider"]),slug(o["title"]),esc(display_offer_title(o)),esc(offer_saving(o)),esc(format_checked(o.get("fetched_at","")))) for o in offers)
    item_list={"@context":"https://schema.org","@type":"ItemList","itemListElement":[{"@type":"ListItem","position":i,"url":BASE+"/deals/{}-{}.html".format(slug(o["provider"]),slug(o["title"]))} for i,o in enumerate(offers,1)]}
    compare_body='<section class="hero compact"><p class="eyebrow">Side by side</p><h1>Compare offers</h1><p>Compare savings and source check dates. Store terms apply.</p></section><label class="compare-sort">Sort by<select id="compare-sort"><option value="featured">Store name</option><option value="discount">Highest % off</option><option value="newest">Recently checked</option></select></label><div class="table-wrap" role="region" aria-label="Offer comparison" tabindex="0"><table><caption class="sr-only">Current official store offers</caption><thead><tr><th scope="col">Store</th><th scope="col">Offer</th><th scope="col">Savings</th><th scope="col">Source check</th></tr></thead><tbody>{}</tbody></table></div>{}'.format(rows or '<tr><td colspan="4">No offers listed.</td></tr>',jsonld(item_list))
    (SITE/"compare.html").write_text(page("Compare Deals | TrueDealAtlas","Compare currently active official promotions",compare_body,"/compare.html","compare.html"),encoding="utf-8")
    for o in offers:
        path="/deals/{}-{}.html".format(slug(o["provider"]),slug(o["title"])); fields={"price":o["price"],"priceCurrency":o["currency"]} if o.get("price") and o.get("currency") else {}; schema={"@context":"https://schema.org","@type":"Offer","name":o["title"],"url":BASE+path,"seller":{"@type":"Organization","name":o["provider"]},**fields}
        dbody='<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Coupons & deals</a><span>/</span><a href="/providers/{}.html">{}</a><span>/</span><span>Offer</span></nav><article class="detail offer-detail"><p class="eyebrow">{} official offer</p><h1>{}</h1><div class="detail-saving">{}</div><p class="checked">{}</p>{}<a class="button detail-cta" href="{}" target="_blank" rel="nofollow noopener">Get deal at {} {}<span class="sr-only"> (opens in a new tab)</span></a><h2>Offer terms</h2><p>{}</p><h2>Eligibility & conditions</h2><p>{}</p><p class="source-note">Source checked means the offer text was found on the official page. Availability and eligibility can change; confirm the terms before checking out.</p><p class="source">Official source: <a href="{}" target="_blank" rel="noopener">{}{}</a></p>{}</article>'.format(slug(o["provider"]),esc(o["provider"]),esc(o["provider"]),esc(display_offer_title(o)),esc(offer_saving(o)),esc(format_checked(o.get("fetched_at",""))),copy_control(o),esc(o["offer_url"]),esc(o["provider"]),icon("arrow-up-right"),esc(o.get("offer_text","")),esc(o.get("conditions","See store for terms.")),esc(o["source_url"]),esc(o["source_url"]),'<span class="sr-only"> (opens in a new tab)</span>',jsonld(schema))
        target=SITE/path.lstrip("/"); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(page(o["provider"]+" Offer | TrueDealAtlas",o["title"]+" from "+o["provider"]+", checked from the official source.",dbody,path),encoding="utf-8")
    (SITE/"guides").mkdir(exist_ok=True)
    for old_guide in (SITE/"guides").glob("*.html"):
        old_guide.unlink()
    guide_links=[]
    for article in articles:
        apath="/guides/{}.html".format(slug(article["slug"]))
        sections="".join("<section><h2>{}</h2>{}</section>".format(esc(section["heading"]),"".join("<p>{}</p>".format(esc(paragraph)) for paragraph in section.get("paragraphs",[]))) for section in article.get("sections",[]))
        faq="".join("<section><h3>{}</h3><p>{}</p></section>".format(esc(item["question"]),esc(item["answer"])) for item in article.get("faq",[]))
        sources="".join('<li><a href="{}" rel="nofollow noopener">{}</a></li>'.format(esc(source["url"]),esc(source["label"])) for source in article.get("sources",[]))
        abody='<article class="detail"><p class="eyebrow">Shopping guide</p><h1>{}</h1><p class="answer"><strong>Answer:</strong> {}</p><p class="muted">Published {}</p>{}<h2>Questions shoppers ask</h2>{}<h2>Sources</h2><ul>{}</ul></article>'.format(esc(article["title"]),esc(article["answer"]),esc(article.get("published_at","")),sections,faq,sources)
        (SITE/apath.lstrip("/")).write_text(page(article["title"]+" | TrueDealAtlas",article.get("description",article["title"]),abody,apath),encoding="utf-8")
        guide_links.append('<li><a href="{}">{}</a><p class="muted">{}</p></li>'.format(apath,esc(article["title"]),esc(article.get("description",""))))
    existing_guide_slugs={slug(article["slug"]) for article in articles}
    brand_slugs=[slug(item["slug"]) for item in brand_pages]
    if len(brand_slugs)!=len(set(brand_slugs)) or existing_guide_slugs.intersection(brand_slugs):
        raise ValueError("Duplicate brand coupon or guide path detected")
    for item in brand_pages:
        apath="/guides/{}.html".format(slug(item["slug"]))
        public_path=apath.removesuffix(".html")
        (SITE/apath.lstrip("/")).write_text(page(item["title"]+" | TrueDealAtlas",item["answer"],brand_coupon_content(item),public_path,footer_brand=item["brand"]),encoding="utf-8")
        guide_links.append('<li><a href="{}">{}</a><p class="muted">Official {} offers and terms.</p></li>'.format(public_path,esc(item["title"]),esc(item["brand"])))
    guides_body='<section class="hero compact"><p class="eyebrow">Evidence-led answers</p><h1>Shopping guides</h1><p>Short answers built from official offer pages and public shopper questions.</p></section><ul class="provider-list">{}</ul>'.format("".join(guide_links) or '<li class="muted">No guides published yet.</li>')
    (SITE/"guides"/"index.html").write_text(page("Shopping Guides | TrueDealAtlas","Evidence-led answers about US brand coupons and offers.",guides_body,"/guides/","provider.html"),encoding="utf-8")
    urls=["/","/compare.html","/providers/","/guides/","/about.html","/privacy.html","/contact.html"]+["/providers/{}.html".format(slug(p["name"])) for p in data.get("providers",[])]+["/deals/{}-{}.html".format(slug(o["provider"]),slug(o["title"])) for o in offers]+["/guides/{}.html".format(slug(a["slug"])) for a in articles]; lastmod=esc(data.get("generated_at",datetime.now(timezone.utc).isoformat())); brand_urls=[("/guides/{}".format(slug(item["slug"])),item["offers"][0]["checked"]) for item in brand_pages]; (SITE/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+"".join("<url><loc>{}{}</loc><lastmod>{}</lastmod></url>".format(BASE,u,lastmod) for u in urls)+"".join("<url><loc>{}{}</loc><lastmod>{}</lastmod></url>".format(BASE,u,esc(checked)) for u,checked in brand_urls)+"</urlset>",encoding="utf-8"); (SITE/"robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: {}/sitemap.xml\n".format(BASE),encoding="utf-8"); (SITE/".ilang").mkdir(exist_ok=True); (SITE/".ilang"/"site.ilang").write_text((ROOT/".ilang"/"site.ilang").read_text(encoding="utf-8"),encoding="utf-8")
STYLES=(ROOT/"templates"/"styles.css").read_text(encoding="utf-8")
SITE_JS=(ROOT/"templates"/"site.js").read_text(encoding="utf-8")
if __name__ == "__main__": build()
