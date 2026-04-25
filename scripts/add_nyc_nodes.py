#!/usr/bin/env python3
"""Add NYC hyperlocal nodes — communities, grid infrastructure, data centers,
datasets, anchor institutions, financial mechanisms, media/advocacy — plus
high-value demo traversal edges.

Designed for the demo path:
  South Bronx → grid stress → data centers → community harm → Chelsea UTEN solution
"""

import os
import sys
from pathlib import Path
from neo4j import GraphDatabase


def get_neo4j_config():
    uri = os.getenv("NEO4J_URI", "")
    password = os.getenv("NEO4J_PASSWORD", "")
    user = os.getenv("NEO4J_USER", "neo4j")
    if not uri:
        env_path = Path(__file__).parent.parent / "backend" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key == "NEO4J_URI": uri = val
                elif key == "NEO4J_PASSWORD": password = val
                elif key == "NEO4J_USER": user = val
    return uri, user, password


# ---------------------------------------------------------------------------
# Node definitions by category
# ---------------------------------------------------------------------------

COMMUNITY_NODES = [
    ("South Bronx CD1", "Community", "South Bronx Community District 1 — Mott Haven, Port Morris. Highest energy burden in NYC, 34% of income spent on utilities. Designated Disadvantaged Community under CLCPA."),
    ("South Bronx CD2", "Community", "South Bronx Community District 2 — Hunts Point, Longwood. Industrial corridor adjacent to data center growth zone. Heavy truck traffic, worst air quality in NYC."),
    ("Mott Haven", "Community", "South Bronx neighborhood with highest energy burden in NYC. Low-income residents pay disproportionate utility rates driven by grid infrastructure costs. Prime candidate for thermal energy network benefits."),
    ("Hunts Point", "Community", "South Bronx industrial zone adjacent to data center expansion. Hosts NYC's largest food distribution center. Grid infrastructure here serves industrial loads while residential customers bear rate increases."),
    ("Washington Heights", "Community", "Upper Manhattan neighborhood — high-density, gas-dependent building stock. Significant LL97 exposure in aging multifamily buildings. 78% of buildings use steam or gas heat."),
    ("East New York", "Community", "Brooklyn DAC with major LL97 exposure. Aging housing stock, high NYCHA concentration. One of NYC's highest rates of heat complaints per capita."),
    ("Sunset Park", "Community", "Brooklyn industrial waterfront — active data center growth zone. Industry Row along 3rd Avenue hosts growing compute infrastructure alongside residential community."),
    ("Long Island City", "Community", "Queens neighborhood hosting NYC's largest data center cluster. Con Edison reports 400+ MW of pending DC interconnection requests in this zone alone."),
    ("Astoria", "Community", "Queens neighborhood defined by power generation history. Home to Astoria Generating Station and NRG peaker plants. Grid nexus point where generation meets distribution."),
]

GRID_NODES = [
    ("NYISO Zone J", "Infrastructure", "New York City electricity load zone managed by NYISO. Peak demand ~11,300 MW. Data center applications represent 1,400+ MW of pending interconnection — 12% of peak load. Most constrained zone in NY state."),
    ("NYISO Zone G", "Infrastructure", "Hudson Valley electricity zone — upstream transmission constraint for NYC. Indian Point retirement removed 2,069 MW from this zone, forcing increased imports through congested transmission corridors."),
    ("Con Edison Service Territory", "Infrastructure", "Con Edison serves 3.4M electric customers across NYC and Westchester. Largest urban utility in US. Facing unprecedented load growth from data centers — 7,000 MW in interconnection queue as of 2024."),
    ("Indian Point Energy Center", "Infrastructure", "Nuclear plant in Buchanan, NY — retired April 2021. Provided 2,069 MW of carbon-free baseload power to NYC. Retirement created capacity gap that data centers are filling with gas-backed demand. Grid emissions rose 15% post-closure."),
    ("Astoria Generating Station", "Infrastructure", "1,800 MW gas-fired power plant in Queens. Provides critical peaking capacity for NYC. Community advocates have fought expansion for decades due to air quality impacts on Astoria and adjacent neighborhoods."),
    ("BQDM Program", "Infrastructure", "Brooklyn-Queens Demand Management — Con Edison's $1.2B non-wires alternative program. Reduced peak demand by 69 MW through efficiency and distributed resources. Model for how utilities can manage load without new substations."),
    ("Con Edison Steam System", "Infrastructure", "Manhattan district steam system — 105 miles of pipes serving 1,500+ buildings. Largest commercial steam system in the world. Existing thermal infrastructure that could integrate with new thermal energy networks."),
    ("Neptune Transmission Cable", "Infrastructure", "65-mile undersea HVDC cable connecting Long Island to New Jersey. 660 MW capacity. Example of major grid infrastructure built to address regional capacity constraints."),
]

DC_NODES = [
    ("Equinix NY4", "Facility", "Major data center in Secaucus, NJ — primary interconnection hub feeding NYC financial district. 47 MW critical load. Waste heat dissipated to atmosphere, zero recovery."),
    ("Equinix NY5", "Facility", "Secaucus carrier hotel and interconnection point. Paired with NY4 for redundancy. Combined 80+ MW serving NYC metro financial and cloud workloads."),
    ("DataBank NYC", "Facility", "Formerly Latisys — NYC colocation provider. Growing footprint in Manhattan and NJ metro. Part of the 1,400+ MW pipeline of DC capacity seeking NYC grid interconnection."),
    ("CyrusOne NYC", "Facility", "Enterprise data center operator with NYC metro presence. Part of the wave of hyperscale-adjacent facilities driving grid strain in NYISO Zone J."),
    ("EdgeConneX NYC", "Facility", "Edge data center operator with NYC deployments. Named in DC fund documentation as growth-stage operator. Smaller facilities closer to end users — distributed grid load impact."),
    ("111 8th Avenue", "Facility", "Google's NYC headquarters — 2.9M sq ft building in Chelsea. Massive power draw from one of NYC's largest single-tenant tech facilities. Located in the same neighborhood as the Chelsea UTEN pilot. A hyperscaler literally next door to the thermal recovery solution."),
    ("60 Hudson Street", "Facility", "Major carrier hotel in Lower Manhattan — one of the most interconnected buildings in the world. Hundreds of telecom and data tenants. Critical node in NYC's digital infrastructure."),
    ("32 Avenue of the Americas", "Facility", "Telehouse-operated carrier hotel in Lower Manhattan. High-density compute loads in a building from 1932. Waste heat vented directly to Tribeca streets."),
]

DATASET_NODES = [
    ("NYC LL84 Energy Disclosure", "Signal", "NYC Building Energy & Water Data Disclosure — annual benchmarking of buildings >25,000 sq ft. Covers 60,000+ buildings. Shows which buildings consume most energy and where LL97 fines will hit hardest."),
    ("NYC LL97 Emissions Benchmarking", "Signal", "LL97 emissions intensity data by building — tracks carbon performance against 2024 and 2030 caps. Buildings exceeding caps face $268/tCO₂ penalties. Hospital and NYCHA exposure is severe."),
    ("NYCHA Heat Complaint Data", "Signal", "NYC Housing Authority residential heat and hot water outage records. Chronic underinvestment means 56,000+ reported heat outages annually. These complaints ARE the demand signal for thermal energy networks."),
    ("NYC311 Heat Complaints", "Signal", "Real-time 311 service requests for heat and hot water — maps directly onto communities that would benefit most from thermal energy networks. Public, geocoded, and updated daily. The complaint data is the demand signal for the solution."),
    ("NYC Community Energy Profiles", "Signal", "CUNY Building Performance Lab data on energy consumption by community district. Shows per-capita energy burden variations of 3x across NYC neighborhoods. South Bronx districts consistently worst."),
    ("HMDA Mortgage Data NYC", "Signal", "Home Mortgage Disclosure Act data by NYC neighborhood. Connects energy burden to housing affordability and fair lending patterns. Energy costs above 6% of income correlate with mortgage denial rates."),
    ("NYC Delivery Worker Survey", "Signal", "NYC DCWP survey of delivery workers — connects gig economy to energy infrastructure through e-bike charging demand and warehouse energy use. Cross-category hackathon relevance."),
]

ANCHOR_NODES = [
    ("Lincoln Hospital", "Institution", "NYC Health+Hospitals facility in South Bronx — 362-bed public hospital. LL97 exposed with estimated $2.1M annual carbon penalty by 2030. Massive thermal load (heating, cooling, sterilization) makes it ideal UTEN heat offtaker."),
    ("Jacobi Medical Center", "Institution", "NYC Health+Hospitals facility in the Bronx — 457 beds. Major thermal energy consumer. LL97 penalties projected at $1.8M/year by 2030. Could anchor a Bronx thermal energy network."),
    ("Montefiore Medical Center", "Institution", "Academic medical center in the Bronx — 1,491 beds across multiple campuses. Largest employer in the Bronx. LL97 exposure estimated at $4.5M annual penalties. Has expressed interest in district energy solutions."),
    ("NYCHA Ravenswood Houses", "Institution", "NYCHA development in Long Island City, Queens — 2,166 units adjacent to LIC data center cluster. Chronic heat outages. Waste heat from nearby DCs could serve this campus at near-zero marginal cost."),
    ("NYC DOE Buildings", "Institution", "NYC Department of Education operates 1,800+ school buildings — collectively the largest LL97-exposed portfolio in the city. Estimated $50M+ in annual carbon penalties by 2030. Schools are natural thermal network anchor loads."),
    ("NYC HPD", "Institution", "NYC Housing Preservation & Development — oversees affordable housing stock. HPD buildings face LL97 compliance costs that threaten affordable rent levels. Thermal networks offer a compliance pathway that doesn't raise rents."),
]

FINANCIAL_NODES = [
    ("NY Green Bank", "Organization", "NYSERDA's $1B green investment fund. Provides credit enhancement and co-lending for clean energy projects. Has financed $2.4B in clean energy projects statewide. Key capital source for UTEN development."),
    ("EmPower+ Program", "Organization", "NYSERDA's low-income energy efficiency program. Provides no-cost energy upgrades to income-eligible households. Could be expanded to include thermal network connections for DAC residents."),
    ("LL97 Fine Structure", "Regulation", "Local Law 97 carbon penalty: $268 per metric ton of CO₂ above building-specific caps. 2024 caps affect ~5,000 buildings. 2030 caps (40% stricter) will affect 20,000+ buildings. Penalties create financial incentive for thermal network offtake."),
    ("PACE Financing", "Organization", "Property Assessed Clean Energy — long-term financing repaid through property tax assessments. Enables building owners to finance thermal network connections with no upfront cost. NYC C-PACE program launched 2022."),
    ("NYC Accelerator", "Organization", "NYC's free building decarbonization advisory program. Helps building owners navigate LL97 compliance, access incentives, and plan retrofits. Could serve as intake funnel for UTEN offtaker recruitment."),
    ("Justice40 Initiative", "Regulation", "Federal mandate: 40% of climate and clean energy investment benefits must flow to Disadvantaged Communities. South Bronx, East New York, and other NYC DACs qualify. Creates federal funding pathway for UTEN projects in these communities."),
    ("NYSERDA Heat Recovery Program", "Organization", "State program incentivizing waste heat capture from industrial and commercial sources. Provides up to $1M per project for heat recovery equipment. Directly applicable to DC waste heat capture for thermal networks."),
]

MEDIA_NODES = [
    ("Food & Water Watch NY", "Organization", "Environmental advocacy org with active NYC campaigns against data center expansion and gas infrastructure. Key voice in the S9144 moratorium debate. Organizes community opposition in South Bronx and LIC."),
    ("NYC Environmental Justice Alliance", "Organization", "Coalition of community-based orgs in DACs across NYC. Advocates for equitable climate policy. Instrumental in shaping LL97 and CLCPA implementation. Potential ally for UTEN community engagement."),
    ("NRDC New York", "Organization", "Natural Resources Defense Council's NYC office — leads litigation and policy advocacy on building emissions, grid planning, and environmental justice. Published key analysis of DC energy impacts."),
    ("The City NYC", "Organization", "Nonprofit investigative newsroom covering NYC. Published groundbreaking reporting on NYCHA heat outages, LL97 implementation gaps, and data center energy consumption. Key media node for public awareness."),
    ("Data Center Watch", "Organization", "Industry tracking publication monitoring data center development, power procurement, and community impacts. Source for real-time intelligence on DC pipeline and grid interconnection queues."),
]


# ---------------------------------------------------------------------------
# Edge definitions — the demo traversal and high-value connections
# ---------------------------------------------------------------------------

EDGES = [
    # === CORE DEMO TRAVERSAL: South Bronx → grid → DCs → harm → UTEN solution ===
    ("NYISO Zone J", "GRID_STRESS_FROM", "Long Island City", "400+ MW of pending DC interconnection requests concentrated in LIC drive grid stress across Zone J"),
    ("Long Island City", "RATE_IMPACT_ON", "South Bronx CD1", "Infrastructure costs for DC interconnection in LIC are socialized across Con Edison ratepayers — South Bronx residents pay higher rates for infrastructure serving data centers"),
    ("South Bronx CD1", "DAC_DESIGNATION", "Justice40 Initiative", "South Bronx CD1 qualifies as Disadvantaged Community under both CLCPA and federal Justice40 — eligible for 40% of federal climate investment"),
    ("NYCHA Heat Complaint Data", "EVIDENCE_OF", "LL97 Fine Structure", "Chronic NYCHA heat outages documented in complaint data reveal the same building-level thermal failures that LL97 fines are designed to address"),
    ("LL97 Fine Structure", "FINANCIAL_PRESSURE_ON", "Lincoln Hospital", "Lincoln Hospital faces estimated $2.1M annual LL97 penalties by 2030 — creating urgent financial incentive to find low-carbon thermal solutions"),
    ("Lincoln Hospital", "POTENTIAL_OFFTAKER_FOR", "Chelsea UTEN", "Lincoln Hospital's massive thermal load (heating, cooling, sterilization) makes it an ideal anchor offtaker for thermal energy network heat recovery"),

    # === EASTER EGG 1: Google next door to UTEN ===
    ("111 8th Avenue", "LOCATED_IN", "Chelsea UTEN", "Google's 2.9M sq ft NYC HQ at 111 8th Ave is in Chelsea — the same neighborhood as the UTEN pilot recovering DC waste heat. A hyperscaler literally next door to the solution."),
    ("111 8th Avenue", "WASTE_HEAT_SOURCE_FOR", "Chelsea UTEN", "111 8th Avenue's massive compute load generates waste heat that could feed directly into the Chelsea UTEN thermal loop"),
    ("Chelsea UTEN", "HEAT_SOURCE", "85 Tenth Avenue", "Chelsea UTEN pilot recovers waste heat from data center operations at 85 10th Ave — Google-adjacent facility"),

    # === EASTER EGG 2: Indian Point → DC gap ===
    ("Indian Point Energy Center", "RETIREMENT_CREATED_GAP", "NYISO Zone G", "Indian Point's 2021 retirement removed 2,069 MW of carbon-free baseload from Zone G — the largest single-plant closure in NY history"),
    ("NYISO Zone G", "CAPACITY_GAP_FILLED_BY", "NYISO Zone J", "Post-Indian Point capacity gap in Zone G increased imports through congested transmission to Zone J, where data centers filled demand faster than renewables"),
    ("NYISO Zone J", "DC_LOAD_GROWTH_TRIGGERED", "S9144", "1,400+ MW of DC interconnection requests in Zone J triggered legislative response — Senator Krueger introduced S9144 moratorium on new DC construction"),
    ("S9144", "REGULATORY_OFFRAMP_VIA", "UTENJA", "S9144 moratorium includes exception pathway for DCs that participate in thermal energy networks — UTENJA provides the enabling framework"),

    # === EASTER EGG 3: 311 complaints → UTEN demand signal ===
    ("NYC311 Heat Complaints", "DEMAND_SIGNAL_FOR", "UTENJA", "311 heat complaint patterns map directly onto communities where thermal energy networks would have greatest impact — complaint data IS the demand signal for the solution"),
    ("NYC311 Heat Complaints", "CONCENTRATED_IN", "South Bronx CD1", "South Bronx CD1 has highest per-capita 311 heat complaints in NYC — 3.2x the citywide average"),
    ("NYC311 Heat Complaints", "CONCENTRATED_IN", "East New York", "East New York has 2.8x citywide average of 311 heat complaints — NYCHA buildings drive the majority"),
    ("NYCHA Ravenswood Houses", "ADJACENT_TO", "Long Island City", "NYCHA Ravenswood Houses sit directly adjacent to LIC data center cluster — waste heat travels less than 0.5 miles to serve 2,166 units"),
    ("NYCHA Ravenswood Houses", "POTENTIAL_OFFTAKER_FOR", "Long Island City", "Ravenswood's chronic heat outages could be solved by waste heat recovery from adjacent LIC data centers at near-zero marginal cost"),

    # === Grid infrastructure connections ===
    ("Con Edison Service Territory", "MANAGES", "NYISO Zone J", "Con Edison is the primary distribution utility for NYISO Zone J — all DC interconnections in NYC flow through Con Ed infrastructure"),
    ("Indian Point Energy Center", "SUPPLIED_POWER_TO", "Con Edison Service Territory", "Indian Point provided 25% of NYC's electricity before retirement — Con Ed had to find replacement capacity, much of it gas-fired"),
    ("Astoria Generating Station", "PEAKING_CAPACITY_FOR", "NYISO Zone J", "Astoria's 1,800 MW provides critical peaking capacity for NYC — runs during heat waves when DC cooling loads spike"),
    ("BQDM Program", "DEMAND_REDUCTION_IN", "Long Island City", "Brooklyn-Queens Demand Management reduced 69 MW of peak load — proving non-wires alternatives work, but insufficient against 400+ MW of DC demand"),
    ("Con Edison Steam System", "THERMAL_INFRASTRUCTURE_IN", "Chelsea UTEN", "Manhattan's existing 105-mile steam system provides thermal infrastructure backbone that UTEN could integrate with or parallel"),
    ("Neptune Transmission Cable", "CAPACITY_FOR", "NYISO Zone J", "Neptune's 660 MW undersea cable supplements Zone J capacity — but data center queue alone exceeds this by 2x"),

    # === Data center → community impact edges ===
    ("Equinix NY4", "GRID_LOAD_ON", "NYISO Zone J", "Equinix NY4's 47 MW load contributes to Zone J congestion — costs socialized across all Con Ed ratepayers"),
    ("Equinix NY5", "GRID_LOAD_ON", "NYISO Zone J", "Equinix NY5 combined with NY4 exceeds 80 MW — larger than many NYC neighborhoods' total consumption"),
    ("60 Hudson Street", "GRID_LOAD_ON", "NYISO Zone J", "60 Hudson's hundreds of telecom and data tenants create concentrated power demand in Lower Manhattan"),
    ("32 Avenue of the Americas", "WASTE_HEAT_TO", "Astoria", "32 Avenue of the Americas vents waste heat directly to Tribeca streets — zero recovery from high-density compute in a 1932 building"),
    ("Sunset Park", "DC_GROWTH_ZONE", "NYISO Zone J", "Sunset Park's industrial waterfront is an active data center growth zone — community faces both construction disruption and grid cost impacts"),
    ("CyrusOne NYC", "GRID_LOAD_ON", "NYISO Zone J", "CyrusOne's enterprise DC operations contribute to the hyperscale wave driving Zone J grid strain"),
    ("EdgeConneX NYC", "DISTRIBUTED_LOAD_ON", "NYISO Zone J", "EdgeConneX's edge facilities distribute smaller loads across Zone J — but collectively add to grid pressure"),

    # === Anchor institution → financial mechanism edges ===
    ("Lincoln Hospital", "LL97_EXPOSURE", "LL97 Fine Structure", "Lincoln Hospital estimated $2.1M annual LL97 penalty by 2030 — one of the largest single-building exposures in the Bronx"),
    ("Jacobi Medical Center", "LL97_EXPOSURE", "LL97 Fine Structure", "Jacobi Medical Center faces $1.8M/year LL97 penalties — thermal network connection could eliminate most of this exposure"),
    ("Montefiore Medical Center", "LL97_EXPOSURE", "LL97 Fine Structure", "Montefiore's multi-campus footprint faces $4.5M annual LL97 penalties — largest medical center exposure in the Bronx"),
    ("NYC DOE Buildings", "LL97_EXPOSURE", "LL97 Fine Structure", "1,800+ DOE school buildings collectively face $50M+ in annual LL97 penalties — largest exposed portfolio in NYC"),
    ("NYC HPD", "COMPLIANCE_PATHWAY_VIA", "UTENJA", "HPD's affordable housing stock needs LL97 compliance pathways that don't raise rents — thermal networks offer this"),

    # === Financial flows ===
    ("NY Green Bank", "CAPITAL_FOR", "Chelsea UTEN", "NY Green Bank provides credit enhancement for UTEN projects — key capital source reducing development risk"),
    ("PACE Financing", "ENABLES_CONNECTION_TO", "UTENJA", "C-PACE financing lets building owners connect to thermal networks with zero upfront cost — repaid through property tax assessments"),
    ("NYC Accelerator", "INTAKE_FOR", "UTENJA", "NYC Accelerator serves as advisory intake funnel — helps building owners understand thermal network benefits and navigate connection"),
    ("EmPower+ Program", "LOW_INCOME_ACCESS_TO", "UTENJA", "EmPower+ could be expanded to cover thermal network connection costs for income-eligible households in DACs"),
    ("NYSERDA Heat Recovery Program", "INCENTIVIZES", "Chelsea UTEN", "Up to $1M per project for heat recovery equipment — directly applicable to DC waste heat capture for UTEN"),
    ("Justice40 Initiative", "FEDERAL_FUNDING_FOR", "South Bronx CD1", "Justice40 mandates 40% of federal climate investment flows to DACs — South Bronx qualifies for UTEN development funding"),
    ("Justice40 Initiative", "FEDERAL_FUNDING_FOR", "East New York", "East New York qualifies as federal DAC — eligible for Justice40 climate investment for thermal network development"),

    # === Dataset → insight edges ===
    ("NYC LL84 Energy Disclosure", "BENCHMARKS", "NYC DOE Buildings", "LL84 data reveals DOE building energy profiles — identifies highest-consuming schools as priority UTEN offtakers"),
    ("NYC LL97 Emissions Benchmarking", "TRACKS_COMPLIANCE_OF", "Lincoln Hospital", "LL97 benchmarking data shows Lincoln Hospital's emissions trajectory vs. 2024 and 2030 caps"),
    ("NYC Community Energy Profiles", "SHOWS_BURDEN_IN", "South Bronx CD1", "CUNY data shows South Bronx CD1 residents spend 34% of income on energy — 3x the citywide median"),
    ("NYC Community Energy Profiles", "SHOWS_BURDEN_IN", "Mott Haven", "Mott Haven energy burden data reveals the human cost of grid infrastructure serving data centers"),
    ("HMDA Mortgage Data NYC", "CORRELATES_WITH", "NYC LL84 Energy Disclosure", "HMDA data shows energy burden above 6% of income correlates with higher mortgage denial rates — connecting energy infrastructure to housing justice"),
    ("NYCHA Heat Complaint Data", "DOCUMENTS_FAILURES_AT", "NYCHA Ravenswood Houses", "Ravenswood Houses heat outage records show 340+ complaints in a single winter — chronic thermal infrastructure failure adjacent to DC waste heat"),

    # === Media / advocacy connections ===
    ("Food & Water Watch NY", "ADVOCATES_FOR", "S9144", "Food & Water Watch is lead organizer supporting S9144 moratorium — mobilizes community opposition to unchecked DC expansion"),
    ("NYC Environmental Justice Alliance", "SHAPED", "LL97 Fine Structure", "NYCEJ Alliance was instrumental in shaping LL97's equity provisions — ensures penalties drive solutions in DACs, not just affluent buildings"),
    ("NRDC New York", "PUBLISHED_ANALYSIS_OF", "NYISO Zone J", "NRDC published key analysis of data center energy impacts on Zone J grid — foundational research for S9144"),
    ("The City NYC", "INVESTIGATED", "NYCHA Heat Complaint Data", "The City published groundbreaking reporting connecting NYCHA heat outages to broader grid infrastructure failures"),
    ("Data Center Watch", "TRACKS", "NYISO Zone J", "Industry tracker monitoring DC pipeline and interconnection queue in Zone J — source for real-time grid impact data"),

    # === Community → community connections ===
    ("Mott Haven", "PART_OF", "South Bronx CD1", "Mott Haven is the core neighborhood of South Bronx CD1 — ground zero for energy burden and environmental justice advocacy"),
    ("Hunts Point", "PART_OF", "South Bronx CD2", "Hunts Point anchors South Bronx CD2 — industrial corridor with highest truck traffic and worst air quality in NYC"),
    ("South Bronx CD1", "SHARES_GRID_WITH", "South Bronx CD2", "CD1 and CD2 share Con Edison distribution infrastructure — rate impacts from DC growth affect both districts"),
    ("Astoria", "HOSTS", "Astoria Generating Station", "Astoria community has lived with power generation impacts for decades — 1,800 MW plant shapes local air quality and grid economics"),
    ("Long Island City", "HOSTS", "NYCHA Ravenswood Houses", "LIC's data center cluster and NYCHA's Ravenswood Houses coexist within 0.5 miles — waste heat and need separated only by infrastructure decisions"),
]


def run(tx, query, **params):
    tx.run(query, **params)


def main():
    uri, user, password = get_neo4j_config()
    if not uri:
        print("ERROR: No NEO4J_URI found"); sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        print("Connected to Neo4j\n")

        # --- Add nodes by category ---
        categories = [
            ("NYC Community", COMMUNITY_NODES),
            ("Grid & Utility Infrastructure", GRID_NODES),
            ("Data Center", DC_NODES),
            ("NYC Dataset", DATASET_NODES),
            ("Anchor Institution", ANCHOR_NODES),
            ("Financial Mechanism", FINANCIAL_NODES),
            ("Media & Advocacy", MEDIA_NODES),
        ]

        total_nodes = 0
        for cat_name, nodes in categories:
            print(f"Adding {cat_name} nodes...")
            for name, ntype, desc in nodes:
                session.execute_write(
                    lambda tx, n=name, t=ntype, d=desc: tx.run(
                        """
                        MERGE (n {name: $name})
                        ON CREATE SET n.type = $type, n.description = $desc, n.source = 'nyc_hyperlocal'
                        ON MATCH SET n.description = $desc, n.source = COALESCE(n.source, 'nyc_hyperlocal')
                        """,
                        name=n, type=t, desc=d,
                    )
                )
                total_nodes += 1
            print(f"  → {len(nodes)} nodes")

        # --- Add edges ---
        print(f"\nCreating {len(EDGES)} edges...")
        edge_count = 0
        for src, rel_type, tgt, desc in EDGES:
            result = session.execute_write(
                lambda tx, s=src, r=rel_type, t=tgt, d=desc: tx.run(
                    """
                    MATCH (a {name: $src})
                    MATCH (b {name: $tgt})
                    MERGE (a)-[r:""" + r + """]->(b)
                    SET r.description = $desc
                    RETURN COUNT(r) as cnt
                    """,
                    src=s, tgt=t, desc=d,
                ).single()
            )
            if result and result["cnt"] > 0:
                edge_count += 1
            else:
                # Try partial name matching
                result2 = session.execute_write(
                    lambda tx, s=src, r=rel_type, t=tgt, d=desc: tx.run(
                        """
                        MATCH (a) WHERE a.name CONTAINS $src OR $src CONTAINS a.name
                        MATCH (b) WHERE b.name CONTAINS $tgt OR $tgt CONTAINS b.name
                        WITH a, b LIMIT 1
                        MERGE (a)-[r:""" + r + """]->(b)
                        SET r.description = $desc
                        RETURN COUNT(r) as cnt
                        """,
                        src=s, tgt=t, desc=d,
                    ).single()
                )
                if result2 and result2["cnt"] > 0:
                    edge_count += 1
                else:
                    print(f"  ⚠ Could not match: {src} -[{rel_type}]-> {tgt}")

        print(f"  → {edge_count} edges created")

        # --- Final stats ---
        stats = session.run(
            """
            MATCH (n)
            RETURN n.type AS type, COUNT(*) AS cnt
            ORDER BY cnt DESC
            """
        ).values()
        total = sum(r[1] for r in stats)
        edge_total = session.run("MATCH ()-[r]->() RETURN COUNT(r) AS cnt").single()["cnt"]
        print(f"\n{'='*50}")
        print(f"Final graph: {total} nodes, {edge_total} edges")
        for t, c in stats:
            print(f"  {t:30s} {c}")
        print("\nDone!")

    driver.close()


if __name__ == "__main__":
    main()
