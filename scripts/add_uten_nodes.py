#!/usr/bin/env python3
"""Add UTEN / Thermal Energy Network nodes and edges to existing Neo4j graph.

Matches existing nodes (Con Edison, NYSERDA, etc.) and creates new ones.
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


def run(driver, cypher, params=None):
    with driver.session(database="neo4j") as s:
        result = s.run(cypher, params or {})
        return [r.data() for r in result]


def merge_node(driver, label, name, props):
    """MERGE a node by name — updates if exists, creates if not."""
    set_clauses = ", ".join(f"n.{k} = ${k}" for k in props)
    cypher = f"MERGE (n:{label} {{name: $name}}) ON CREATE SET {set_clauses} ON MATCH SET {set_clauses} RETURN n"
    run(driver, cypher, {"name": name, **props})


def merge_edge(driver, from_label, from_name, to_label, to_name, rel_type, props=None):
    """Create an edge between two nodes matched by name."""
    prop_str = ""
    if props:
        prop_str = " {" + ", ".join(f"{k}: ${k}" for k in props) + "}"
    cypher = (
        f"MATCH (a:{from_label} {{name: $from_name}}), (b:{to_label} {{name: $to_name}}) "
        f"CREATE (a)-[:{rel_type}{prop_str}]->(b)"
    )
    run(driver, cypher, {"from_name": from_name, "to_name": to_name, **(props or {})})


def main():
    uri, user, password = get_neo4j_config()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("Connected to Neo4j\n")

    # =========================================================================
    # 1. LEGISLATION & POLICY
    # =========================================================================
    print("Adding Legislation & Policy nodes...")

    legislation = {
        "NY Senate Bill S9144": {
            "description": "Proposed NY State bill requiring data centers >20MW to capture and redistribute waste heat via thermal energy networks. Would mandate heat recovery systems for new DC construction and major expansions in NYC metro area. Sponsored by Sen. Liz Krueger.",
            "jurisdiction": "NY State",
            "status": "Proposed",
            "year": 2024,
        },
        "NY Assembly Bill A10141": {
            "description": "Assembly companion to S9144. Requires large data centers to implement waste heat recovery and connect to district heating networks. Sponsored by Assemblymember Anna Kelles. Includes provisions for disadvantaged community priority.",
            "jurisdiction": "NY State",
            "status": "Proposed",
            "year": 2024,
        },
        "UTENJA (Utility Thermal Energy Network & Jobs Act)": {
            "description": "2022 NY State law enabling gas utilities to own and operate thermal energy networks (TENs). Allows Con Edison and National Grid to build geothermal loop systems using existing gas infrastructure rights-of-way. First-in-nation utility TEN framework.",
            "jurisdiction": "NY State",
            "status": "Enacted",
            "year": 2022,
        },
        "IRA Section 48 ITC": {
            "description": "Federal Investment Tax Credit under the Inflation Reduction Act providing 30-50% tax credits for geothermal heat pump systems and district energy networks. Bonus credits for projects in disadvantaged communities and using domestic content.",
            "jurisdiction": "Federal",
            "status": "Enacted",
            "year": 2022,
        },
    }

    for name, props in legislation.items():
        merge_node(driver, "Regulation", name, props)
    print(f"  → {len(legislation)} legislation nodes")

    # =========================================================================
    # 2. ACTIVE PROJECTS
    # =========================================================================
    print("Adding Active Project nodes...")

    projects = {
        "Chelsea UTEN Pilot": {
            "description": "Con Edison's flagship thermal energy network pilot in Manhattan's Chelsea neighborhood. Captures waste heat from 85 Tenth Avenue data center tenants (Google, others) and redistributes to NYCHA Fulton Houses and nearby buildings. Uses ambient-temperature water loops with distributed heat pumps. 36 buildings, ~2,000 residential units served.",
            "type": "thermal_energy_network",
            "location": "Chelsea, Manhattan, NY",
            "operator": "Con Edison",
            "capacity_mw": 8,
            "status": "In Development",
        },
        "Rockefeller Center UTEN Pilot": {
            "description": "Con Edison thermal energy network serving Rockefeller Center complex. Captures waste heat from commercial cooling systems and redistributes for heating. Engineering by WSP. Demonstrates commercial district TEN viability with premium real estate.",
            "type": "thermal_energy_network",
            "location": "Midtown Manhattan, NY",
            "operator": "Con Edison",
            "capacity_mw": 12,
            "status": "In Development",
        },
        "Mount Vernon UTEN Pilot": {
            "description": "Con Edison suburban thermal energy network pilot in Mount Vernon, Westchester County. Tests TEN deployment in lower-density residential areas. Key test case for scaling beyond Manhattan.",
            "type": "thermal_energy_network",
            "location": "Mount Vernon, NY",
            "operator": "Con Edison",
            "capacity_mw": 3,
            "status": "Planning",
        },
        "Syracuse Inner Harbor UTEN": {
            "description": "National Grid thermal energy network at Syracuse Inner Harbor mixed-use development. Integrates geothermal boreholes with lake water source. First National Grid TEN project under UTENJA authorization.",
            "type": "thermal_energy_network",
            "location": "Syracuse, NY",
            "operator": "National Grid",
            "capacity_mw": 5,
            "status": "In Development",
        },
        "Brooklyn Vandalia Ave UTEN": {
            "description": "National Grid thermal energy network in East New York, Brooklyn. Targets disadvantaged community with high energy burden. Uses abandoned gas infrastructure corridors for thermal loop installation. Environmental justice priority project.",
            "type": "thermal_energy_network",
            "location": "East New York, Brooklyn, NY",
            "operator": "National Grid",
            "capacity_mw": 4,
            "status": "Planning",
        },
        "Ithaca UTEN": {
            "description": "NYSEG (Avangrid) thermal energy network pilot in Ithaca, NY. Serves Cornell University adjacent neighborhoods. Tests cold-climate TEN performance. Connected to Ithaca's ambitious Green New Deal electrification goals.",
            "type": "thermal_energy_network",
            "location": "Ithaca, NY",
            "operator": "NYSEG",
            "capacity_mw": 3,
            "status": "In Development",
        },
    }

    for name, props in projects.items():
        merge_node(driver, "Facility", name, props)
    print(f"  → {len(projects)} project nodes")

    # =========================================================================
    # 3. KEY ORGANIZATIONS (merge with existing where possible)
    # =========================================================================
    print("Adding/merging Organization nodes...")

    orgs = {
        "NY Green Bank": {
            "description": "State-capitalized $1B green investment bank. Provides low-cost financing for clean energy projects including thermal energy networks. Key funding source for UTEN pilots.",
        },
        "NY Dept. of Environmental Conservation": {
            "description": "NY DEC — regulates environmental permits. Issues Generic Environmental Impact Statements (GEIS) for thermal energy networks. Key permitting authority for TEN installations.",
        },
        "National Grid": {
            "description": "Major gas utility serving upstate NY, Brooklyn, Queens, and Long Island. Authorized under UTENJA to build and operate thermal energy networks. Operating Syracuse and Brooklyn UTEN pilots.",
        },
        "NYSEG": {
            "description": "New York State Electric & Gas (Avangrid subsidiary). Electric and gas utility serving central/western NY. Operating Ithaca UTEN pilot under UTENJA authorization.",
        },
        "NYCHA Fulton Houses": {
            "description": "NYC Housing Authority's Fulton Houses in Chelsea — 11-building, 944-unit public housing complex. Primary heat sink for Chelsea UTEN pilot, receiving waste heat from nearby data centers. Residents would save an estimated 30-40% on heating costs.",
        },
        "85 Tenth Ave Associates": {
            "description": "Joint venture of Related Companies and Vornado Realty Trust. Owns 85 Tenth Avenue, a 630,000 sq ft former Nabisco factory converted to tech office/data center space. Google is anchor tenant. Primary waste heat source for Chelsea UTEN — data center cooling produces ~6MW of recoverable thermal energy.",
        },
        "Food & Water Watch": {
            "description": "Environmental advocacy organization. Key opponent of data center expansion without waste heat mandates. Lobbying for S9144 passage. Published reports on DC water consumption impact.",
        },
        "WSP": {
            "description": "Global engineering firm. Engineer of record for both Chelsea and Rockefeller Center UTEN pilots. Designed the ambient-loop thermal distribution system. Leading TEN design expertise in North America.",
        },
    }

    for name, props in orgs.items():
        merge_node(driver, "Organization", name, props)
    print(f"  → {len(orgs)} organization nodes")

    # =========================================================================
    # 4. KEY POLITICAL FIGURES
    # =========================================================================
    print("Adding Political Figure nodes...")

    politicians = {
        "Sen. Liz Krueger": {
            "title": "NY State Senator",
            "organization": "NY State Senate",
            "category": "Policy/Regulatory",
            "impact_score": 8.5,
            "expertise": "Primary sponsor of S9144 data center waste heat mandate. Chair of Senate Finance Committee. Manhattan district includes major data center corridors. Leading voice on DC energy accountability.",
            "region": "NYC Metro",
            "expert_id": "NYC-POL-001",
        },
        "Assemblymember Anna Kelles": {
            "title": "NY State Assemblymember",
            "organization": "NY State Assembly",
            "category": "Policy/Regulatory",
            "impact_score": 8.0,
            "expertise": "Sponsor of A10141 (Assembly companion to S9144). PhD in public health. Expert on environmental justice and energy equity. Ithaca district — home of NYSEG UTEN pilot.",
            "region": "NY State",
            "expert_id": "NYC-POL-002",
        },
        "Sen. Kristen Gonzalez": {
            "title": "NY State Senator, Chair of Senate Technology Committee",
            "organization": "NY State Senate",
            "category": "Policy/Regulatory",
            "impact_score": 8.0,
            "expertise": "Co-sponsor of S9144. Chairs Senate Internet and Technology Committee — key jurisdiction over data center regulation. Queens district directly impacted by DC power demand on NYISO Zone J grid.",
            "region": "NYC Metro",
            "expert_id": "NYC-POL-003",
        },
    }

    for name, props in politicians.items():
        merge_node(driver, "Person", name, props)
    print(f"  → {len(politicians)} political figure nodes")

    # =========================================================================
    # 5. TECHNICAL CONCEPTS
    # =========================================================================
    print("Adding Technical Concept nodes...")

    concepts = {
        "Thermal Energy Network (TEN)": {
            "description": "District-scale system of underground water pipes connecting buildings for shared heating and cooling. Buildings with excess heat (data centers, commercial cooling) supply thermal energy to buildings needing heat (residential, hospitals). Replaces gas boilers with electric heat pumps. 300-400% efficient via COP multiplier.",
        },
        "5th Generation District Heating & Cooling": {
            "description": "Latest evolution of district energy: ambient-temperature water loops (15-25°C) with distributed heat pumps at each building. Unlike traditional steam/hot water district heating, 5GDHC enables bidirectional energy flow — any building can be source or sink. Lower pipe losses, no insulation needed.",
        },
        "Water-Source Heat Pump": {
            "description": "Electric heat pump using water as its thermal source/sink instead of air. COP of 4-6 (vs 2-3 for air-source). Core technology enabling thermal energy networks. Each building installs its own WSHP connected to the shared ambient loop.",
        },
        "Coefficient of Performance (COP)": {
            "description": "Ratio of useful heating/cooling to electricity input. A COP of 4 means 1 kWh of electricity produces 4 kWh of thermal energy. Water-source heat pumps achieve COP 4-6. Key metric making TENs economically viable — 3-4x more efficient than electric resistance heating.",
        },
        "Thermal Energy Storage (TES)": {
            "description": "Storing thermal energy in insulated water tanks or underground boreholes for later use. Enables load-shifting: store excess data center heat during day, distribute for heating at night. Reduces peak electricity demand. Ice storage variant handles cooling peaks.",
        },
        "Ambient Loop System": {
            "description": "The core distribution architecture of 5th-gen thermal networks. Uninsulated pipes circulate water at near-ambient temperatures (15-25°C). Each building's heat pump extracts or rejects heat to the loop. Bidirectional flow enables waste heat sharing between buildings.",
        },
        "Data Center Waste Heat Recovery": {
            "description": "Capturing the thermal energy rejected by data center cooling systems (typically 30-45°C) and upgrading it via heat pumps for building heating. A 10MW data center produces enough waste heat to warm ~2,000 apartments. Currently wasted to atmosphere in virtually all US data centers.",
        },
        "Generic Environmental Impact Statement (GEIS)": {
            "description": "NY State environmental review covering an entire category of projects rather than individual ones. A GEIS for thermal energy networks would streamline permitting by pre-analyzing common environmental impacts, reducing per-project review time from 12-18 months to 2-3 months.",
        },
    }

    for name, props in concepts.items():
        merge_node(driver, "Concept", name, props)
    print(f"  → {len(concepts)} concept nodes")

    # =========================================================================
    # 6. MARKET & RISK FACTORS
    # =========================================================================
    print("Adding Market & Risk Factor nodes...")

    signals_data = {
        "NY Residential Electricity Rate Increase": {
            "description": "NYC residential electricity rates surged 43% from 2020 to 2025, driven by infrastructure upgrades, clean energy mandates, and rising natural gas costs. Makes heat pump economics increasingly favorable vs. gas heating. Con Edison Zone J rates highest in continental US at $0.33/kWh.",
            "source_type": "market_data",
            "sentiment": "bearish",
            "sentiment_score": -0.6,
        },
        "NYISO 1.6 GW Grid Shortfall": {
            "description": "NYISO projects a 1.6 GW capacity shortfall in Zone J (NYC) by 2030 due to data center load growth, EV adoption, and building electrification. Existing peaker plants retiring under CLCPA. Champlain Hudson (1.25GW) and Clean Path (1.3GW) transmission lines only partially close the gap. Data centers are the fastest-growing load category.",
            "source_type": "grid_analysis",
            "sentiment": "bearish",
            "sentiment_score": -0.8,
        },
        "DC Water Consumption Risk": {
            "description": "If US data center capacity triples by 2030 (as projected), cooling water demand would equal 18.5 million household equivalents. NYC faces acute water stress — DC cooling towers compete with residential supply. Drives demand for air-cooled and heat-recovery systems that eliminate cooling tower water waste.",
            "source_type": "environmental",
            "sentiment": "bearish",
            "sentiment_score": -0.7,
        },
        "20 MW Threshold (DC Moratorium Trigger)": {
            "description": "Proposed regulatory threshold in S9144: data centers exceeding 20MW must implement waste heat recovery and connect to thermal energy networks. Below 20MW exempt. Affects all major NYC-area facilities (Equinix, Digital Realty, CoreWeave average 25-130MW). Strategic threshold chosen to exempt small edge DCs while capturing hyperscale.",
            "source_type": "policy",
            "sentiment": "neutral",
            "sentiment_score": 0.0,
        },
        "Disadvantaged Community Designation": {
            "description": "NY Climate Justice Working Group (CJWG) criteria identifying communities bearing disproportionate environmental burdens. UTEN projects in designated areas receive priority permitting, enhanced IRA tax credits (40-50% vs 30%), and NY Green Bank favorable financing. Brooklyn Vandalia and Chelsea (NYCHA) qualify.",
            "source_type": "policy",
            "sentiment": "bullish",
            "sentiment_score": 0.5,
        },
    }

    for name, props in signals_data.items():
        merge_node(driver, "Signal", name, {**props, "signal_id": f"uten-{name[:20].lower().replace(' ', '_')}"})
    print(f"  → {len(signals_data)} market signal nodes")

    # =========================================================================
    # 7. INTERNATIONAL PRECEDENTS
    # =========================================================================
    print("Adding International Precedent nodes...")

    precedents = {
        "Meta Odense Data Center": {
            "description": "Meta's hyperscale data center in Odense, Denmark. Captures 100% of waste heat and feeds it into Fjernvarme Fyn's district heating network, warming 12,000+ homes. World's largest DC waste heat recovery project. Proves the model at hyperscale — produces 100MW thermal.",
            "type": "data_center",
            "location": "Odense, Denmark",
            "capacity_mw": 100,
            "operator": "Meta Platforms",
        },
        "Fjernvarme Fyn": {
            "description": "District heating operator serving 120,000 households in Odense, Denmark. Partnered with Meta to integrate data center waste heat into existing district heating grid. Reduced gas consumption 25%. Business model: Meta pays zero for heat rejection (saves cooling costs), Fjernvarme sells heat to customers at lower rates than gas.",
        },
        "Stockholm Open District Heating": {
            "description": "Stockholm Exergi's open district heating network. Accepts waste heat from 100+ sources including data centers, supermarkets, and sewage treatment. Data centers provide 10% of Stockholm's district heating. Open platform model allows any heat source to sell into the network at spot prices.",
        },
        "False Creek Neighbourhood Energy Utility": {
            "description": "Vancouver's municipal district energy utility serving 6,000 residential units using sewer heat recovery. Heat pumps extract thermal energy from sewage mains at COP 3.5. Proves urban waste heat recovery at municipal scale. Model for NYC sewer heat potential.",
        },
        "Ramboll": {
            "description": "Danish engineering firm that designed the Meta Odense waste heat recovery system. Global leader in district energy and thermal network engineering. Consulting on multiple North American TEN projects. Key knowledge holder for scaling DC heat recovery.",
        },
    }

    for name, props in precedents.items():
        if "type" in props and props["type"] == "data_center":
            merge_node(driver, "Facility", name, props)
        else:
            merge_node(driver, "Organization", name, props)
    print(f"  → {len(precedents)} international precedent nodes")

    # =========================================================================
    # 8. EDGES — the interesting connections
    # =========================================================================
    print("\nCreating edges...")
    edge_count = 0

    # --- Legislation edges ---
    edges = [
        # S9144 connections
        ("Regulation", "NY Senate Bill S9144", "Signal", "20 MW Threshold (DC Moratorium Trigger)", "TARGETS"),
        ("Regulation", "NY Senate Bill S9144", "Concept", "Thermal Energy Network (TEN)", "MANDATES"),
        ("Regulation", "NY Senate Bill S9144", "Concept", "Data Center Waste Heat Recovery", "MANDATES"),
        ("Signal", "NYISO 1.6 GW Grid Shortfall", "Regulation", "NY Senate Bill S9144", "STRENGTHENS_CASE_FOR"),

        # A10141 connections
        ("Regulation", "NY Assembly Bill A10141", "Regulation", "NY Senate Bill S9144", "COMPANION_BILL"),
        ("Regulation", "NY Assembly Bill A10141", "Concept", "Thermal Energy Network (TEN)", "MANDATES"),

        # UTENJA enables all pilots
        ("Regulation", "UTENJA (Utility Thermal Energy Network & Jobs Act)", "Facility", "Chelsea UTEN Pilot", "ENABLES"),
        ("Regulation", "UTENJA (Utility Thermal Energy Network & Jobs Act)", "Facility", "Rockefeller Center UTEN Pilot", "ENABLES"),
        ("Regulation", "UTENJA (Utility Thermal Energy Network & Jobs Act)", "Facility", "Mount Vernon UTEN Pilot", "ENABLES"),
        ("Regulation", "UTENJA (Utility Thermal Energy Network & Jobs Act)", "Facility", "Syracuse Inner Harbor UTEN", "ENABLES"),
        ("Regulation", "UTENJA (Utility Thermal Energy Network & Jobs Act)", "Facility", "Brooklyn Vandalia Ave UTEN", "ENABLES"),
        ("Regulation", "UTENJA (Utility Thermal Energy Network & Jobs Act)", "Facility", "Ithaca UTEN", "ENABLES"),

        # LL97 drives TEN demand
        ("Regulation", "Local Law 97", "Concept", "Thermal Energy Network (TEN)", "CREATES_DEMAND_FOR"),
        ("Regulation", "Local Law 97", "Concept", "Data Center Waste Heat Recovery", "CREATES_DEMAND_FOR"),

        # CLCPA context
        ("Regulation", "NY CLCPA", "Regulation", "UTENJA (Utility Thermal Energy Network & Jobs Act)", "MOTIVATES"),
        ("Regulation", "NY CLCPA", "Signal", "NYISO 1.6 GW Grid Shortfall", "CONTRIBUTES_TO"),

        # IRA incentives
        ("Regulation", "IRA Section 48 ITC", "Concept", "Thermal Energy Network (TEN)", "INCENTIVIZES"),
        ("Regulation", "IRA Section 48 ITC", "Signal", "Disadvantaged Community Designation", "ENHANCED_BY"),

        # --- Chelsea UTEN core edges ---
        ("Facility", "Chelsea UTEN Pilot", "Organization", "85 Tenth Ave Associates", "HEAT_SOURCE"),
        ("Facility", "Chelsea UTEN Pilot", "Organization", "NYCHA Fulton Houses", "HEAT_SINK"),
        ("Organization", "Con Edison", "Facility", "Chelsea UTEN Pilot", "OPERATES"),
        ("Organization", "WSP", "Facility", "Chelsea UTEN Pilot", "ENGINEERED_BY"),
        ("Organization", "WSP", "Facility", "Rockefeller Center UTEN Pilot", "ENGINEERED_BY"),

        # Other project operators
        ("Organization", "Con Edison", "Facility", "Rockefeller Center UTEN Pilot", "OPERATES"),
        ("Organization", "Con Edison", "Facility", "Mount Vernon UTEN Pilot", "OPERATES"),
        ("Organization", "National Grid", "Facility", "Syracuse Inner Harbor UTEN", "OPERATES"),
        ("Organization", "National Grid", "Facility", "Brooklyn Vandalia Ave UTEN", "OPERATES"),
        ("Organization", "NYSEG", "Facility", "Ithaca UTEN", "OPERATES"),

        # Politician sponsorship
        ("Person", "Sen. Liz Krueger", "Regulation", "NY Senate Bill S9144", "SPONSORS"),
        ("Person", "Assemblymember Anna Kelles", "Regulation", "NY Assembly Bill A10141", "SPONSORS"),
        ("Person", "Sen. Kristen Gonzalez", "Regulation", "NY Senate Bill S9144", "CO_SPONSORS"),

        # Org → regulation
        ("Organization", "Food & Water Watch", "Regulation", "NY Senate Bill S9144", "ADVOCATES_FOR"),
        ("Organization", "NY Green Bank", "Concept", "Thermal Energy Network (TEN)", "FINANCES"),
        ("Organization", "NY Dept. of Environmental Conservation", "Concept", "Generic Environmental Impact Statement (GEIS)", "ISSUES"),
        ("Organization", "NYSERDA", "Facility", "Chelsea UTEN Pilot", "FUNDS"),
        ("Organization", "NYSERDA", "Facility", "Brooklyn Vandalia Ave UTEN", "FUNDS"),
        ("Organization", "NY Public Service Commission", "Regulation", "UTENJA (Utility Thermal Energy Network & Jobs Act)", "REGULATES_UNDER"),

        # International precedents → concepts
        ("Facility", "Meta Odense Data Center", "Concept", "Data Center Waste Heat Recovery", "DEMONSTRATES"),
        ("Facility", "Meta Odense Data Center", "Concept", "5th Generation District Heating & Cooling", "IMPLEMENTS"),
        ("Organization", "Fjernvarme Fyn", "Facility", "Meta Odense Data Center", "RECEIVES_HEAT_FROM"),
        ("Organization", "Stockholm Open District Heating", "Concept", "Thermal Energy Network (TEN)", "OPERATES"),
        ("Organization", "Ramboll", "Facility", "Meta Odense Data Center", "DESIGNED"),

        # Concepts → technical links
        ("Concept", "Thermal Energy Network (TEN)", "Concept", "5th Generation District Heating & Cooling", "INSTANCE_OF"),
        ("Concept", "Ambient Loop System", "Concept", "Thermal Energy Network (TEN)", "CORE_TECHNOLOGY_OF"),
        ("Concept", "Water-Source Heat Pump", "Concept", "Thermal Energy Network (TEN)", "CORE_TECHNOLOGY_OF"),
        ("Concept", "Thermal Energy Storage (TES)", "Concept", "Thermal Energy Network (TEN)", "ENHANCES"),
        ("Concept", "Coefficient of Performance (COP)", "Concept", "Water-Source Heat Pump", "MEASURES_EFFICIENCY_OF"),

        # DC companies impacted by S9144
        ("Regulation", "NY Senate Bill S9144", "Company", "Applied Digital", "WOULD_REGULATE"),
        ("Regulation", "NY Senate Bill S9144", "Company", "Core Scientific", "WOULD_REGULATE"),
        ("Regulation", "NY Senate Bill S9144", "Company", "CoreWeave", "WOULD_REGULATE"),

        # Bloom Energy benefits from TEN ecosystem
        ("Company", "Bloom Energy", "Concept", "Thermal Energy Network (TEN)", "SYNERGY_WITH"),

        # Market signals → companies
        ("Signal", "NY Residential Electricity Rate Increase", "Organization", "Con Edison", "DRIVEN_BY"),
        ("Signal", "NYISO 1.6 GW Grid Shortfall", "Organization", "NYISO", "PROJECTED_BY"),
        ("Signal", "DC Water Consumption Risk", "Concept", "Data Center Waste Heat Recovery", "MOTIVATES"),

        # 85 Tenth Ave connects to Google (existing company concept)
        ("Organization", "85 Tenth Ave Associates", "Facility", "Digital Realty 111 8th Ave", "ADJACENT_TO"),

        # Disadvantaged community → Brooklyn project
        ("Signal", "Disadvantaged Community Designation", "Facility", "Brooklyn Vandalia Ave UTEN", "QUALIFIES"),
        ("Signal", "Disadvantaged Community Designation", "Organization", "NYCHA Fulton Houses", "QUALIFIES"),
    ]

    for from_label, from_name, to_label, to_name, rel_type in edges:
        try:
            merge_edge(driver, from_label, from_name, to_label, to_name, rel_type)
            edge_count += 1
        except Exception as e:
            print(f"  WARN: Edge failed {from_name} → {to_name}: {e}")

    print(f"  → {edge_count} edges created")

    # =========================================================================
    # VERIFY
    # =========================================================================
    print("\n" + "=" * 50)
    result = run(driver, "MATCH (n) RETURN count(n) AS nodes")
    nodes = result[0]["nodes"]
    result = run(driver, "MATCH ()-[r]->() RETURN count(r) AS edges")
    edges_total = result[0]["edges"]
    print(f"Final graph: {nodes} nodes, {edges_total} edges")

    # New node counts
    result = run(driver, "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC")
    for r in result:
        print(f"  {r['label']:20s} {r['count']:>6d}")

    driver.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
