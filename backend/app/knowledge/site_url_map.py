"""Mapping of NIEL product categories and specific equipment subtypes to live website URLs.

All URLs are verified against https://newindiaelectricals.com sitemap and navigation.
"""

from typing import Dict, List, Optional
import re

BASE_SITE_URL = "https://newindiaelectricals.com"

# Exact product ID to live URL mapping
PRODUCT_ID_URL_MAP: Dict[str, str] = {
    # AC Motors
    "ac-cage-rotor": f"{BASE_SITE_URL}/ac-motors/closed-cage-type-motors/",
    "ac-wound-rotor": f"{BASE_SITE_URL}/ac-motors/wound-close-type-motors/",
    "ac-flameproof": f"{BASE_SITE_URL}/ac-motors/flame-proof-motors/",
    "ac-crane-duty": f"{BASE_SITE_URL}/ac-motors/crane-duty-slipring-motors/",
    "ac-mill-duty": f"{BASE_SITE_URL}/ac-motors/rerolling-mill-duty-motors/",
    "ac-roller-table": f"{BASE_SITE_URL}/ac-motors/roller-table-motors/",
    
    # DC Motors
    "dc-industrial-motors": f"{BASE_SITE_URL}/dc-motors/",
    
    # Transformers
    "transformer-distribution": f"{BASE_SITE_URL}/transformers/distribution-transformer/",
    "transformer-power": f"{BASE_SITE_URL}/transformers/power-transformer/",
    "transformer-furnace": f"{BASE_SITE_URL}/transformers/furnace-transformer/",
    "transformer-cast-resin-dry": f"{BASE_SITE_URL}/transformers/cast-resin-dry-type-transformers/",
    "substation-containerised-css": f"{BASE_SITE_URL}/transformers/containerised-secondary-substations-css/",
    
    # Switchgear & Panels
    "switchgear-power-plus-v": f"{BASE_SITE_URL}/switchgear-panels/medium-voltage-panels/power-v/",
    "switchgear-power-plus-f": f"{BASE_SITE_URL}/switchgear-panels/medium-voltage-panels/power-f/",
    "switchgear-power-plus-vo": f"{BASE_SITE_URL}/switchgear-panels/medium-voltage-panels/power-vo/",
    "switchgear-lv-panels": f"{BASE_SITE_URL}/switchgear-panels/low-voltage-panels/",
    
    # Pumps & Valves
    "pump-end-suction-monoblock": f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/end-suction-monoblock-pump/",
    "pump-openwell-submersible": f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/open-well-submersible-pumpkos/",
    "pump-end-suction-process": f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/end-suction-process-pump-kpd/",
    "pump-self-priming-nonclog": f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/non-clog-self-priming-pump-sp-spm/",
    "pump-vacuum": f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/vacuum-pumps/",
    "pump-vertical-in-line-multistage": f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/vertical-inline-multistage-pump/",
    "pump-horizontal-multistage": f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/horizontal-multistage-pumps-rkb/",
    "valves-industrial": f"{BASE_SITE_URL}/valves/",
    
    # Drives
    "drive-lv-ac": f"{BASE_SITE_URL}/low-voltage-ac-drives/",
    "drive-dc-thyristor": f"{BASE_SITE_URL}/drives/dc-drives/",
    
    # Gearboxes & Brake Motors
    "gear-worm-speed-reducers": f"{BASE_SITE_URL}/gear-box/worm-gear-box/",
    "gear-helical-geared-motors": f"{BASE_SITE_URL}/gear-motors/",
    "gear-helical-shaft-mounted": f"{BASE_SITE_URL}/gear-box/helical-gear-box/",
    "gear-cycloidal-drives": f"{BASE_SITE_URL}/gear-box/",
    "motors-brake-integral": f"{BASE_SITE_URL}/brake-motors/",
    
    # Substation Systems
    "substation-turnkey-epc": f"{BASE_SITE_URL}/substation-systems/",
}

# Category-level fallback URLs
CATEGORY_URL_MAP: Dict[str, str] = {
    "ac_motors": f"{BASE_SITE_URL}/ac-motors/",
    "ac motors": f"{BASE_SITE_URL}/ac-motors/",
    "dc_motors": f"{BASE_SITE_URL}/dc-motors/",
    "dc motors": f"{BASE_SITE_URL}/dc-motors/",
    "transformers": f"{BASE_SITE_URL}/transformers/",
    "transformer": f"{BASE_SITE_URL}/transformers/",
    "switchgear": f"{BASE_SITE_URL}/switchgear-panels/",
    "switchgear_panels": f"{BASE_SITE_URL}/switchgear-panels/",
    "switchgear panels": f"{BASE_SITE_URL}/switchgear-panels/",
    "pumps_and_valves": f"{BASE_SITE_URL}/pumps-valves/",
    "pumps and valves": f"{BASE_SITE_URL}/pumps-valves/",
    "pumps": f"{BASE_SITE_URL}/pumps-valves/",
    "valves": f"{BASE_SITE_URL}/valves/",
    "drives": f"{BASE_SITE_URL}/drives/",
    "ac_dc_drives": f"{BASE_SITE_URL}/drives/",
    "ac/dc drives": f"{BASE_SITE_URL}/drives/",
    "gearboxes": f"{BASE_SITE_URL}/gear-box/",
    "gear-box": f"{BASE_SITE_URL}/gear-box/",
    "gearboxes_and_brake_motors": f"{BASE_SITE_URL}/gear-box/",
    "gearboxes and brake motors": f"{BASE_SITE_URL}/gear-box/",
    "brake_motors": f"{BASE_SITE_URL}/brake-motors/",
    "brake motors": f"{BASE_SITE_URL}/brake-motors/",
    "gear_motors": f"{BASE_SITE_URL}/gear-motors/",
    "gear motors": f"{BASE_SITE_URL}/gear-motors/",
    "substations": f"{BASE_SITE_URL}/substation-systems/",
    "substation_systems": f"{BASE_SITE_URL}/substation-systems/",
    "substation systems": f"{BASE_SITE_URL}/substation-systems/",
}

# Subtype keyword patterns mapped to live URLs
SUBTYPE_KEYWORD_MAP: List[tuple[List[str], str]] = [
    # AC Motor Subtypes
    (["high voltage", "hv motor", "hv motors", "6.6 kv motor", "11 kv motor"], f"{BASE_SITE_URL}/ac-motors/high-voltage-motors/"),
    (["flameproof", "flame proof", "flame-proof", "explosion proof", "hazardous area motor"], f"{BASE_SITE_URL}/ac-motors/flame-proof-motors/"),
    (["crane duty", "crane-duty", "slipring crane"], f"{BASE_SITE_URL}/ac-motors/crane-duty-slipring-motors/"),
    (["cooling tower"], f"{BASE_SITE_URL}/ac-motors/cooling-tower-motors/"),
    (["non sparking", "non-sparking"], f"{BASE_SITE_URL}/ac-motors/non-sparking-motors/"),
    (["vertical hollow shaft", "hollow shaft"], f"{BASE_SITE_URL}/ac-motors/vertical-hollow-shaft-motors/"),
    (["roller table"], f"{BASE_SITE_URL}/ac-motors/roller-table-motors/"),
    (["open type cage", "open cage"], f"{BASE_SITE_URL}/ac-motors/open-type-cage-motors/"),
    (["wound open type"], f"{BASE_SITE_URL}/ac-motors/wound-open-type-motors/"),
    (["wound close type"], f"{BASE_SITE_URL}/ac-motors/wound-close-type-motors/"),
    (["closed cage", "cage rotor", "squirrel cage"], f"{BASE_SITE_URL}/ac-motors/closed-cage-type-motors/"),
    (["rerolling mill", "mill duty ac", "ac mill duty", "re-rolling mill"], f"{BASE_SITE_URL}/ac-motors/rerolling-mill-duty-motors/"),
    
    # DC Motor Subtypes
    (["laminated yoke"], f"{BASE_SITE_URL}/dc-motors/laminated-yoke-motors/"),
    (["mill duty dc", "dc mill duty"], f"{BASE_SITE_URL}/dc-motors/mill-duty-dc-motors/"),
    (["solid yoke"], f"{BASE_SITE_URL}/dc-motors/solid-yoke-dc-motors/"),
    
    # Transformer Subtypes
    (["distribution transformer", "distribution transformers"], f"{BASE_SITE_URL}/transformers/distribution-transformer/"),
    (["power transformer", "power transformers"], f"{BASE_SITE_URL}/transformers/power-transformer/"),
    (["furnace transformer", "furnace transformers"], f"{BASE_SITE_URL}/transformers/furnace-transformer/"),
    (["cast resin", "dry type transformer", "dry type transformers"], f"{BASE_SITE_URL}/transformers/cast-resin-dry-type-transformers/"),
    (["containerised secondary substation", "containerised secondary substations", "compact secondary substation", "compact secondary substations", "compact substation", "compact substations", "css"], f"{BASE_SITE_URL}/transformers/containerised-secondary-substations-css/"),
    
    # Switchgear Subtypes
    (["medium voltage panel", "mv panel", "mv switchgear"], f"{BASE_SITE_URL}/medium-voltage-panels/"),
    (["low voltage panel", "lv panel", "lv switchgear", "mcc panel", "pcc panel", "apfc panel"], f"{BASE_SITE_URL}/switchgear-panels/low-voltage-panels/"),
    (["other panel", "other panels"], f"{BASE_SITE_URL}/other-panels/"),
    (["power+ v", "power v", "vcb panel"], f"{BASE_SITE_URL}/switchgear-panels/medium-voltage-panels/power-v/"),
    (["power+ f", "power f", "sf6 breaker panel"], f"{BASE_SITE_URL}/switchgear-panels/medium-voltage-panels/power-f/"),
    (["power+ vo", "power vo", "kiosk vcb"], f"{BASE_SITE_URL}/switchgear-panels/medium-voltage-panels/power-vo/"),
    
    # Pumps & Valves Subtypes
    (["end suction monoblock", "monoblock pump", "monoblock pumps", "monoblock"], f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/end-suction-monoblock-pump/"),
    (["open well submersible", "open well submersible pump", "open well submersible pumps", "openwell"], f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/open-well-submersible-pumpkos/"),
    (["process pump", "process pumps", "chemical pump", "chemical pumps"], f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/end-suction-process-pump-kpd/"),
    (["self-priming non-clog", "non-clog pump", "non-clog pumps", "non clog", "spm pump"], f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/non-clog-self-priming-pump-sp-spm/"),
    (["vacuum pump", "vacuum pumps", "liquid ring vacuum"], f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/vacuum-pumps/"),
    (["vertical inline multistage", "vertical inline multistage pump", "vertical in-line"], f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/vertical-inline-multistage-pump/"),
    (["horizontal multistage", "horizontal multistage pump", "horizontal multistage pumps"], f"{BASE_SITE_URL}/pumps-valves/centrifugal-pumps/horizontal-multistage-pumps-rkb/"),
    (["centrifugal pump", "centrifugal pumps"], f"{BASE_SITE_URL}/centrifugal-pumps/"),
    (["gear pump", "gear pumps", "nbl del"], f"{BASE_SITE_URL}/nbl-del-gear-pumps/"),
    (["valve", "valves", "sluice valve", "butterfly valve", "gate valve"], f"{BASE_SITE_URL}/valves/"),
    
    # Drives Subtypes
    (["low voltage ac drive", "lv ac drive", "vfd", "variable frequency drive"], f"{BASE_SITE_URL}/low-voltage-ac-drives/"),
    (["medium voltage ac drive", "mv ac drive", "mv drive"], f"{BASE_SITE_URL}/drives/medium-voltage-ac-drives/"),
    (["dc drive", "dc drives", "thyristor drive"], f"{BASE_SITE_URL}/drives/dc-drives/"),
    
    # Gearboxes & Brake Motors Subtypes
    (["worm gear box", "worm gear", "worm speed reducer"], f"{BASE_SITE_URL}/gear-box/worm-gear-box/"),
    (["helical gear box", "helical gear"], f"{BASE_SITE_URL}/gear-box/helical-gear-box/"),
    (["gear motor", "geared motor"], f"{BASE_SITE_URL}/gear-motors/"),
    (["brake motor", "brake motors", "electromagnetic brake"], f"{BASE_SITE_URL}/brake-motors/"),
    
    # Substation Systems
    (["substation", "substations", "turnkey substation"], f"{BASE_SITE_URL}/substation-systems/"),
]


def resolve_site_url(
    product_id: Optional[str] = None,
    category: Optional[str] = None,
    text: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve the matching live URL on newindiaelectricals.com.
    Returns None if there is no confident match. Never fabricates a URL.
    """
    # 1. Exact product ID match
    if product_id and product_id in PRODUCT_ID_URL_MAP:
        return PRODUCT_ID_URL_MAP[product_id]

    # 2. Check query text against specific subtypes
    if text:
        text_lower = text.lower()
        for keywords, url in SUBTYPE_KEYWORD_MAP:
            if any(re.search(rf"\b{re.escape(kw)}\b", text_lower) for kw in keywords):
                return url

    # 3. Category match
    if category:
        clean_cat = category.strip().lower()
        if clean_cat in CATEGORY_URL_MAP:
            return CATEGORY_URL_MAP[clean_cat]
        # Try removing punctuation
        norm_cat = re.sub(r"[^\w\s]", " ", clean_cat).strip()
        if norm_cat in CATEGORY_URL_MAP:
            return CATEGORY_URL_MAP[norm_cat]

    # 4. Fallback: match broad category keywords in text
    if text:
        text_lower = text.lower()
        if "ac motor" in text_lower or "induction motor" in text_lower:
            return f"{BASE_SITE_URL}/ac-motors/"
        if "dc motor" in text_lower:
            return f"{BASE_SITE_URL}/dc-motors/"
        if "transformer" in text_lower:
            return f"{BASE_SITE_URL}/transformers/"
        if "switchgear" in text_lower or "panel" in text_lower:
            return f"{BASE_SITE_URL}/switchgear-panels/"
        if "pump" in text_lower or "pumps" in text_lower:
            return f"{BASE_SITE_URL}/pumps-valves/"
        if "drive" in text_lower or "drives" in text_lower or "vfd" in text_lower:
            return f"{BASE_SITE_URL}/drives/"
        if "gearbox" in text_lower or "gear box" in text_lower:
            return f"{BASE_SITE_URL}/gear-box/"
        if "brake motor" in text_lower:
            return f"{BASE_SITE_URL}/brake-motors/"
        if "substation" in text_lower:
            return f"{BASE_SITE_URL}/substation-systems/"

    return None

