#!/usr/bin/env python3
"""Populate Neo4j with DC & Energy Nexus trading intelligence graph.

Creates ~500+ nodes and ~1800+ edges covering:
- 12 universe stocks + 11 supply chain companies
- 205 experts from CSV
- 6 institutions (hedge funds + passive)
- 5 trading clusters
- 10 regulations (federal + NY state + NYC)
- 6 commodities
- 8 concepts (Leopold thesis, scaling laws, etc.)
- 11 products
- 14 NYC facilities
- 7 NYC organizations
- ~170 signals + orders from nexus.db

Usage:
    python scripts/populate_neo4j.py
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys
from pathlib import Path

from neo4j import GraphDatabase

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

STEALTH_DIR = Path("/Users/lappy/Desktop/STEALTH")
EXPERTS_CSV = STEALTH_DIR / "data" / "experts.csv"
NEXUS_DB = STEALTH_DIR / "data" / "nexus.db"

# Neo4j connection — read from env or .env file
def get_neo4j_config() -> tuple[str, str, str]:
    uri = os.getenv("NEO4J_URI", "")
    password = os.getenv("NEO4J_PASSWORD", "")
    user = os.getenv("NEO4J_USER", "neo4j")

    if not uri:
        # Try reading from backend .env
        env_path = Path(__file__).parent.parent / "backend" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "NEO4J_URI":
                    uri = val
                elif key == "NEO4J_PASSWORD":
                    password = val
                elif key == "NEO4J_USER":
                    user = val

    if not uri:
        print("ERROR: NEO4J_URI not set. Set env vars or check backend/.env")
        sys.exit(1)
    return uri, user, password


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

# 12 universe stocks
STOCKS = {
    "COHR": {"name": "Coherent Corp", "cluster": "FIBER_OPTICS", "stock_type": "structural_hold", "description": "Leading producer of coherent optical transceivers for AI/data center interconnects. Leopold Aschenbrenner core holding."},
    "LITE": {"name": "Lumentum Holdings", "cluster": "FIBER_OPTICS", "stock_type": "structural_hold", "description": "Optical components and photonic chips for cloud and telecom networks. Key supplier to hyperscalers."},
    "CRWV": {"name": "CoreWeave", "cluster": "FIBER_OPTICS", "stock_type": "structural_hold", "description": "GPU cloud provider specializing in AI/ML workloads. Silicon photonics pioneer. NVIDIA's preferred cloud partner."},
    "EQT":  {"name": "EQT Corporation", "cluster": "ENERGY", "stock_type": "structural_hold", "description": "Largest US natural gas producer. Powers data centers. Appalachian basin operations supply NYC region."},
    "APLD": {"name": "Applied Digital", "cluster": "AI_COMPUTE", "stock_type": "active_trade", "description": "Next-gen data center operator for AI/HPC workloads. Building 400MW+ campus in North Dakota."},
    "CORZ": {"name": "Core Scientific", "cluster": "AI_COMPUTE", "stock_type": "active_trade", "description": "Largest publicly traded Bitcoin miner pivoting to AI/HPC hosting. 1.2GW power capacity."},
    "IREN": {"name": "Iris Energy", "cluster": "AI_COMPUTE", "stock_type": "active_trade", "description": "Sustainable Bitcoin miner and AI cloud provider. GPU compute infrastructure with renewable energy focus."},
    "HUT":  {"name": "Hut 8 Mining", "cluster": "CRYPTO_MINERS", "stock_type": "active_trade", "description": "Bitcoin self-mining and managed hosting. Largest Bitcoin reserve on balance sheet among public miners."},
    "CIFR": {"name": "Cipher Mining", "cluster": "CRYPTO_MINERS", "stock_type": "active_trade", "description": "Bitcoin miner with low-cost power in Texas. Strategic PPA portfolio."},
    "RIOT": {"name": "Riot Platforms", "cluster": "CRYPTO_MINERS", "stock_type": "active_trade", "description": "Major Bitcoin miner with 1GW+ Corsicana facility in Texas. ERCOT demand response revenue."},
    "BE":   {"name": "Bloom Energy", "cluster": "ENERGY", "stock_type": "active_trade", "description": "Solid oxide fuel cells for on-site power generation. Data center behind-the-meter solutions bypass grid constraints."},
    "SNDK": {"name": "Sandisk / Western Digital", "cluster": "STORAGE", "stock_type": "active_trade", "description": "NAND flash storage for AI training datasets and inference caching. Hyperscaler storage supplier."},
}

# Supply chain companies (not in trading universe)
SUPPLY_CHAIN_COMPANIES = {
    "TSM":   {"name": "TSMC", "description": "World's largest chip foundry. Fabricates chips for NVIDIA, AMD, Apple. Taiwan-based, building Arizona fab."},
    "ASML":  {"name": "ASML Holdings", "description": "Sole supplier of EUV lithography machines. Controls semiconductor manufacturing bottleneck."},
    "AMAT":  {"name": "Applied Materials", "description": "Leading semiconductor equipment maker. Supplies deposition, etch, and inspection tools to all major fabs."},
    "NVDA":  {"name": "NVIDIA", "description": "Dominant AI GPU supplier. H100/B200 chips power virtually all AI training. $3T+ market cap."},
    "MSFT":  {"name": "Microsoft", "description": "Largest hyperscaler (Azure). $80B+ annual AI capex. OpenAI partnership. Key APLD customer."},
    "AMZN":  {"name": "Amazon", "description": "AWS operates 100+ data centers globally. Building custom AI chips (Trainium). Nuclear power deals."},
    "GOOGL": {"name": "Alphabet / Google", "description": "Google Cloud + DeepMind. TPU AI chips. Major fiber optic customer. Utility demand response pioneer."},
    "META":  {"name": "Meta Platforms", "description": "Building massive AI training clusters. Llama open-source models. 600K+ GPU fleet."},
    "AWK":   {"name": "American Water Works", "description": "Largest US water utility. Data center cooling water supply. Critical infrastructure for DC operations."},
    "LUMN":  {"name": "Lumen Technologies", "description": "Fiber optic network operator. Custom fiber builds for hyperscalers. Dark fiber and wavelength services."},
    "FCX":   {"name": "Freeport-McMoRan", "description": "World's largest publicly traded copper producer. Copper essential for data center power infrastructure."},
}

# Clusters
CLUSTERS = {
    "AI_COMPUTE": {"members": ["APLD", "CORZ", "IREN"], "description": "AI/HPC data center operators transitioning from crypto mining to GPU compute hosting"},
    "CRYPTO_MINERS": {"members": ["HUT", "CIFR", "RIOT"], "description": "Bitcoin mining operations with large-scale power infrastructure and BTC treasury strategies"},
    "FIBER_OPTICS": {"members": ["COHR", "LITE", "CRWV"], "description": "Optical networking and photonics companies enabling AI data center interconnects"},
    "ENERGY": {"members": ["BE", "EQT"], "description": "Energy infrastructure — natural gas production and fuel cell power for data centers"},
    "STORAGE": {"members": ["SNDK"], "description": "Flash storage for AI training data and inference caching at hyperscale"},
}

# Institutions
INSTITUTIONS = {
    "Vanguard Group": {"type": "passive", "holds": list(STOCKS.keys()), "description": "World's largest index fund manager. Holds positions across entire universe through index funds."},
    "BlackRock": {"type": "passive", "holds": list(STOCKS.keys()), "description": "World's largest asset manager ($10T+ AUM). iShares ETFs hold all universe stocks."},
    "State Street": {"type": "passive", "holds": list(STOCKS.keys()), "description": "Third-largest passive manager. SPDR ETFs. Custodian for major institutional portfolios."},
    "Fidelity Investments": {"type": "passive", "holds": list(STOCKS.keys()), "description": "Major active and passive fund manager. Early Bitcoin custody. Holds across all clusters."},
    "ARK Invest": {"type": "active", "holds": ["CORZ", "IREN", "APLD", "BE", "COHR"], "description": "Cathie Wood's innovation-focused fund. Concentrated bets on AI compute and clean energy."},
    "Situational Awareness LP": {"type": "hedge_fund", "holds": ["COHR", "LITE", "CRWV", "APLD", "CORZ", "IREN", "BE", "EQT"], "description": "Leopold Aschenbrenner's $5.5B fund. Thesis: AI compute demand grows 10x by 2027. Core positions in fiber optics and DC operators."},
    "Citadel": {"type": "hedge_fund", "holds": ["NVDA", "COHR", "APLD", "EQT"], "description": "Ken Griffin's multi-strategy hedge fund. Quantitative AI infrastructure plays."},
    "D.E. Shaw": {"type": "hedge_fund", "holds": ["COHR", "LITE", "BE", "EQT"], "description": "Quantitative hedge fund with energy and tech infrastructure conviction."},
    "Renaissance Technologies": {"type": "hedge_fund", "holds": ["COHR", "IREN", "EQT", "BE"], "description": "Jim Simons' Medallion Fund. Systematic trading across DC and energy names."},
    "Tiger Global": {"type": "hedge_fund", "holds": ["CRWV", "APLD", "CORZ"], "description": "Growth equity fund. Early CoreWeave investor. AI infrastructure thesis."},
}

# Regulations — federal + NY state + NYC
REGULATIONS = {
    "CHIPS Act": {
        "description": "CHIPS and Science Act — $52B federal subsidies for domestic semiconductor manufacturing. Reshoring chip production from Asia.",
        "affected": ["COHR", "LITE", "CRWV", "SNDK", "TSM", "ASML", "AMAT"],
        "jurisdiction": "Federal",
    },
    "IRA (Inflation Reduction Act)": {
        "description": "Inflation Reduction Act — $369B for clean energy. Investment tax credits for fuel cells, hydrogen, and energy storage.",
        "affected": ["BE", "EQT", "APLD", "CORZ", "IREN"],
        "jurisdiction": "Federal",
    },
    "FERC Order 2023": {
        "description": "FERC interconnection queue reform. Speeds up grid connection for data centers and power plants. Reduces 5+ year queue backlog.",
        "affected": ["BE", "EQT", "APLD", "CORZ", "IREN"],
        "jurisdiction": "Federal",
    },
    "SEC Climate Disclosure Rule": {
        "description": "SEC mandatory climate risk disclosure. Data centers must report Scope 1/2 emissions. Impacts energy procurement strategy.",
        "affected": ["APLD", "CORZ", "IREN", "HUT", "CIFR", "RIOT"],
        "jurisdiction": "Federal",
    },
    "NY CLCPA": {
        "description": "NY Climate Leadership and Community Protection Act — 70% renewable electricity by 2030, 100% zero-emission by 2040. Impacts all NYC power consumers.",
        "affected": ["APLD", "CORZ", "IREN", "BE", "EQT"],
        "jurisdiction": "NY State",
    },
    "NY Crypto Mining Moratorium": {
        "description": "New York State 2-year moratorium on fossil-fuel-powered crypto mining. Forces miners to use renewables or relocate.",
        "affected": ["RIOT", "HUT", "CIFR", "CORZ"],
        "jurisdiction": "NY State",
    },
    "Local Law 97": {
        "description": "NYC Local Law 97 — building emissions limits starting 2024. Data centers face fines of $268/ton CO2 over cap. Drives behind-the-meter fuel cell adoption.",
        "affected": ["BE", "APLD", "CORZ"],
        "jurisdiction": "NYC",
    },
    "NY PSC Data Center Framework": {
        "description": "NY Public Service Commission framework for data center electricity procurement. Requires load balancing and demand response participation.",
        "affected": ["APLD", "CORZ", "IREN", "CRWV"],
        "jurisdiction": "NY State",
    },
    "CHIPS FABS Act Extension": {
        "description": "Proposed extension of CHIPS Act funding through 2030. Additional $20B for advanced packaging and photonics manufacturing.",
        "affected": ["COHR", "LITE", "CRWV", "TSM"],
        "jurisdiction": "Federal",
    },
    "DOE AI Data Center Efficiency Standards": {
        "description": "Department of Energy proposed PUE standards for AI data centers. Targets PUE < 1.2. Drives efficient cooling and power design.",
        "affected": ["APLD", "CORZ", "IREN", "BE"],
        "jurisdiction": "Federal",
    },
}

# Commodities
COMMODITIES = {
    "Natural Gas (Henry Hub)": {"unit": "$/MMBtu", "price": 3.85, "description": "US natural gas benchmark. Powers 40% of US electricity. Key input cost for data center operators."},
    "Bitcoin": {"unit": "$/BTC", "price": 87250, "description": "Leading cryptocurrency. Mining revenue drives RIOT, HUT, CIFR. Halving cycle affects miner profitability."},
    "Electricity (NYC Zone J)": {"unit": "$/MWh", "price": 85.50, "description": "NYISO Zone J (NYC) wholesale electricity. Highest prices in US. Drives behind-the-meter fuel cell economics."},
    "Crude Oil (WTI)": {"unit": "$/barrel", "price": 71.20, "description": "West Texas Intermediate crude benchmark. Correlated with natural gas. Macro indicator."},
    "GPU Spot (H100)": {"unit": "$/GPU/hour", "price": 2.85, "description": "NVIDIA H100 GPU cloud spot pricing. Key revenue driver for APLD, CORZ, IREN GPU hosting."},
    "Copper": {"unit": "$/lb", "price": 4.65, "description": "Industrial metal essential for data center power infrastructure. Cables, transformers, bus bars."},
}

# Supply chain relationships
SUPPLY_CHAIN = {
    "gpu_demand": [
        ("APLD", 0.9, "GPU hosting revenue — direct customer for NVIDIA GPUs"),
        ("CORZ", 0.85, "GPU compute transition from BTC mining"),
        ("IREN", 0.80, "GPU compute infrastructure buildout"),
        ("HUT", 0.60, "compute diversification from pure mining"),
        ("BE", 0.40, "data center energy demand for GPU clusters"),
        ("EQT", 0.30, "natural gas power for GPU data centers"),
    ],
    "natural_gas_price": [
        ("EQT", 0.95, "direct gas producer — revenue sensitivity"),
        ("BE", 0.50, "fuel cell fuel cost input"),
    ],
    "bitcoin_price": [
        ("RIOT", 0.90, "BTC mining revenue — direct hash rate correlation"),
        ("HUT", 0.85, "BTC mining + 10,000+ BTC treasury reserve"),
        ("CIFR", 0.80, "BTC mining revenue — low-cost Texas operations"),
        ("CORZ", 0.40, "partial BTC mining alongside GPU hosting"),
    ],
    "fiber_optic_demand": [
        ("COHR", 0.90, "coherent optics market leader — 800G/1.6T transceivers"),
        ("LITE", 0.85, "optical components and photonic integrated circuits"),
        ("CRWV", 0.30, "data center connectivity and GPU cluster networking"),
    ],
    "hyperscaler_capex": [
        ("APLD", 0.70, "hosting contracts with Microsoft, Meta"),
        ("COHR", 0.65, "optical infrastructure for cloud buildout"),
        ("LITE", 0.60, "photonic components for DC interconnects"),
        ("SNDK", 0.55, "storage demand from AI training datasets"),
        ("BE", 0.45, "power infrastructure for new DC campuses"),
    ],
    "data_center_build": [
        ("APLD", 0.85, "DC operator — new campus construction"),
        ("CORZ", 0.80, "DC operations — converting mining to AI"),
        ("BE", 0.70, "on-site fuel cell power for new DCs"),
        ("EQT", 0.50, "gas-to-power for DC energy"),
        ("COHR", 0.45, "connectivity for new DC deployments"),
    ],
    "nyc_power_demand": [
        ("BE", 0.90, "behind-the-meter fuel cells for NYC buildings and DCs"),
        ("EQT", 0.70, "gas supply to NYC power plants via pipelines"),
        ("APLD", 0.50, "NYC-adjacent data center power demand"),
        ("CORZ", 0.45, "northeast DC operations power needs"),
    ],
    "nyc_data_center_growth": [
        ("CRWV", 0.85, "CoreWeave NJ campus serves NYC financial workloads"),
        ("COHR", 0.75, "optical interconnects for NYC metro DC cluster"),
        ("APLD", 0.60, "northeast DC expansion"),
        ("BE", 0.55, "fuel cells for NYC data center power"),
    ],
}

# Upstream/downstream supply chain
UPSTREAM = {
    "TSM": ["COHR", "LITE", "CRWV", "APLD", "CORZ", "IREN", "SNDK"],
    "ASML": ["COHR", "LITE", "CRWV", "SNDK"],
    "AMAT": ["COHR", "LITE", "CRWV", "SNDK"],
    "AWK": ["APLD", "CORZ", "IREN"],
    "LUMN": ["APLD", "CORZ", "IREN", "COHR", "LITE"],
    "FCX": ["COHR", "LITE", "CRWV", "BE"],
}

DOWNSTREAM = {
    "NVDA": ["APLD", "CORZ", "IREN", "COHR", "LITE", "CRWV", "SNDK"],
    "MSFT": ["APLD", "CORZ", "IREN", "BE", "EQT"],
    "AMZN": ["APLD", "CORZ", "IREN", "BE", "EQT"],
    "GOOGL": ["APLD", "CORZ", "IREN", "COHR", "LITE"],
    "META": ["APLD", "CORZ", "IREN", "COHR", "LITE"],
}

# Competitor groups
COMPETITOR_GROUPS = [
    ["APLD", "CORZ", "IREN"],
    ["HUT", "CIFR", "RIOT"],
    ["COHR", "LITE"],
]

# Concepts
CONCEPTS = {
    "Leopold's Situational Awareness Thesis": {
        "description": "Leopold Aschenbrenner's thesis that AGI compute demand will grow 10-100x by 2028, requiring massive infrastructure buildout across GPUs, power, and networking.",
        "advocates": ["COHR", "LITE", "CRWV", "APLD", "CORZ", "IREN", "BE", "EQT"],
    },
    "AI Scaling Laws": {
        "description": "Empirical observation that AI model performance scales predictably with compute, data, and parameters. Drives exponential GPU demand.",
        "advocates": ["APLD", "CORZ", "IREN", "NVDA"],
    },
    "Energy Transition": {
        "description": "Global shift from fossil fuels to clean energy. Data center growth accelerates demand for fuel cells, renewables, and grid modernization.",
        "advocates": ["BE", "EQT", "IREN"],
    },
    "Hyperscaler Capex Supercycle": {
        "description": "Multi-year capital expenditure cycle by cloud giants (MSFT, AMZN, GOOGL, META) investing $200B+/year in AI infrastructure.",
        "advocates": ["APLD", "COHR", "LITE", "SNDK", "BE"],
    },
    "BTC Halving Cycle": {
        "description": "Bitcoin's 4-year halving cycle reduces mining rewards, forcing miners to optimize or pivot. Next halving expected April 2028.",
        "advocates": ["HUT", "CIFR", "RIOT", "CORZ"],
    },
    "Behind-the-Meter Power": {
        "description": "On-site power generation bypassing grid constraints. Bloom Energy fuel cells provide 24/7 baseload power at data centers without utility interconnection.",
        "advocates": ["BE", "APLD", "CORZ"],
    },
    "Optical Interconnect Revolution": {
        "description": "Transition from electrical to optical connections inside data centers. 800G→1.6T→3.2T transceivers enable AI cluster scaling.",
        "advocates": ["COHR", "LITE", "CRWV"],
    },
    "NYC as AI Compute Hub": {
        "description": "New York City emerging as premium AI compute market due to financial sector demand, despite highest power costs. Drives behind-the-meter and efficiency innovation.",
        "advocates": ["CRWV", "BE", "COHR", "APLD"],
    },
}

# Products
PRODUCTS = {
    "800G/1.6T Coherent Transceivers": {"producer": "COHR", "category": "Optical Networking", "description": "High-speed coherent optical transceivers for AI data center interconnects. Industry-leading pluggable form factor."},
    "InP Photonic Integrated Circuits": {"producer": "LITE", "category": "Photonics", "description": "Indium phosphide photonic chips for next-gen optical components. Enables 1.6T and beyond."},
    "Silicon Photonics Engines": {"producer": "CRWV", "category": "Photonics", "description": "Co-packaged silicon photonics for GPU cluster networking. Low latency, high bandwidth."},
    "Solid Oxide Fuel Cells": {"producer": "BE", "category": "Power Generation", "description": "Bloom Energy Server — 300kW fuel cells running on natural gas or hydrogen. 65% electrical efficiency."},
    "NAND Flash (BiCS)": {"producer": "SNDK", "category": "Storage", "description": "3D NAND flash memory for AI training data storage and inference caching at hyperscale."},
    "H100/B200 GPUs": {"producer": "NVDA", "category": "AI Compute", "description": "NVIDIA's data center GPUs. H100 ($30K) and B200 ($40K) power virtually all AI training workloads."},
    "EUV Lithography Systems": {"producer": "ASML", "category": "Semiconductor Equipment", "description": "Extreme ultraviolet lithography machines. $380M each. Only ASML makes them. Required for leading-edge chips."},
    "Natural Gas (Marcellus Shale)": {"producer": "EQT", "category": "Energy", "description": "Marcellus Shale natural gas production. Low-cost domestic supply for power generation."},
    "Immersion Cooling Systems": {"producer": "APLD", "category": "Data Center Infrastructure", "description": "Liquid immersion cooling for high-density GPU racks. Enables 100kW+ per rack."},
    "ASIC Bitcoin Miners": {"producer": "RIOT", "category": "Mining Hardware", "description": "Application-specific integrated circuits for SHA-256 Bitcoin mining. Latest gen: 20 J/TH efficiency."},
    "Custom AI Chips (Trainium)": {"producer": "AMZN", "category": "AI Compute", "description": "Amazon's custom AI training chips. Alternative to NVIDIA GPUs for AWS workloads."},
}

# NYC facilities
FACILITIES = {
    "Equinix NY1 (Secaucus)": {"type": "data_center", "location": "Secaucus, NJ", "capacity_mw": 32, "operator": "Equinix", "description": "Major carrier hotel serving NYC financial sector. Low-latency connectivity to Wall Street."},
    "Equinix NY2-NY3 (Secaucus)": {"type": "data_center", "location": "Secaucus, NJ", "capacity_mw": 28, "operator": "Equinix", "description": "Equinix campus expansion. AI/ML workload growth."},
    "Equinix NY4-NY5 (Secaucus)": {"type": "data_center", "location": "Secaucus, NJ", "capacity_mw": 45, "operator": "Equinix", "description": "Flagship financial services data center. NYSE, NASDAQ matching engines."},
    "Equinix NY7-NY11 (Secaucus)": {"type": "data_center", "location": "Secaucus, NJ", "capacity_mw": 60, "operator": "Equinix", "description": "Newest Equinix NYC metro expansion. AI workload optimized. 60MW capacity."},
    "Digital Realty 111 8th Ave": {"type": "data_center", "location": "Manhattan, NY", "capacity_mw": 40, "operator": "Digital Realty", "description": "Iconic Manhattan carrier hotel. Google's NYC headquarters. Premium connectivity hub."},
    "Digital Realty 60 Hudson St": {"type": "data_center", "location": "Manhattan, NY", "capacity_mw": 25, "operator": "Digital Realty", "description": "Historic telecom building. Major peering point. Subsea cable landing."},
    "CoreWeave NJ Campus": {"type": "data_center", "location": "Weehawken, NJ", "capacity_mw": 100, "operator": "CoreWeave", "description": "CoreWeave's flagship GPU cloud campus. NVIDIA H100/B200 clusters serving NYC financial AI workloads."},
    "Ravenswood Power Plant": {"type": "power_plant", "location": "Queens, NY", "capacity_mw": 2480, "operator": "Rise Light & Power", "description": "NYC's largest power plant. Natural gas peaker units. Proposed conversion to clean energy + data center campus."},
    "Champlain Hudson Power Express": {"type": "transmission", "location": "NYC Metro", "capacity_mw": 1250, "operator": "Transmission Developers", "description": "339-mile underwater/underground transmission line bringing Canadian hydropower to NYC. Operational 2026."},
    "Clean Path NY": {"type": "transmission", "location": "NYC Metro", "capacity_mw": 1300, "operator": "Forward Power/NYPA", "description": "Transmission line from upstate wind/solar farms to NYC. Combined with 3.8 GW renewable generation."},
    "Bloom Energy NYC Installations": {"type": "fuel_cell", "location": "Manhattan, NY", "capacity_mw": 15, "operator": "Bloom Energy", "description": "Distributed fuel cell installations at NYC commercial buildings. Behind-the-meter power avoiding Con Edison grid."},
    "QTS Data Center (NJ)": {"type": "data_center", "location": "Piscataway, NJ", "capacity_mw": 130, "operator": "QTS Realty", "description": "Major hyperscale campus serving NYC metro. AI workload growth driving expansion."},
    "DataBank NYC Metro": {"type": "data_center", "location": "Newark, NJ", "capacity_mw": 20, "operator": "DataBank", "description": "Edge data center serving NYC enterprise and financial services."},
    "Hut 8 Ontario Facility": {"type": "mining_facility", "location": "North Bay, Ontario", "capacity_mw": 45, "operator": "Hut 8", "description": "Hut 8's flagship mining facility. Hydropower. Close to US northeast market."},
}

# NYC organizations
NYC_ORGS = {
    "Con Edison": {"description": "NYC's electric utility. Serves 3.4M customers. Key gatekeeper for data center grid connections. Zone J pricing."},
    "NYISO": {"description": "New York Independent System Operator. Manages wholesale electricity market. Zone J has highest prices in US."},
    "NYSERDA": {"description": "NY State Energy Research and Development Authority. Administers clean energy programs and DC efficiency incentives."},
    "NYC Mayor's Office of Sustainability": {"description": "Oversees Local Law 97 implementation. Building emissions enforcement for data centers."},
    "NY Public Service Commission": {"description": "Regulates utilities. Developing data center electricity procurement framework."},
    "Rise Light & Power": {"description": "Owns Ravenswood power plant. Proposing conversion to clean energy campus with on-site data center."},
    "Wall Street Demand Center": {"description": "NYC financial district — largest concentration of low-latency trading data centers. Goldman, JPMorgan, Citadel colocate here."},
}

# Category → relevant tickers (for expert→company edges)
CATEGORY_TO_TICKERS = {
    "AI/Infrastructure": ["APLD", "CORZ", "IREN", "COHR", "LITE", "CRWV", "SNDK", "NVDA"],
    "Energy/Utilities": ["BE", "EQT"],
    "Energy": ["BE", "EQT"],
    "Crypto/Mining": ["HUT", "CIFR", "RIOT", "CORZ"],
    "Policy/Regulatory": ["BE", "EQT", "APLD", "CORZ"],
    "Academic/Think Tank": ["BE", "EQT", "COHR", "LITE"],
    "Financial/Investment": ["COHR", "LITE", "CRWV", "APLD", "CORZ"],
    "Government": ["BE", "EQT", "APLD"],
    "Data Center/Cloud": ["APLD", "CORZ", "IREN", "CRWV"],
    "Telecom/Networking": ["COHR", "LITE", "CRWV"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_query(driver, cypher: str, params: dict | None = None) -> list:
    with driver.session(database="neo4j") as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


def batch_create(driver, cypher: str, rows: list[dict], batch_size: int = 100) -> int:
    """Execute a batched UNWIND query."""
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        run_query(driver, cypher, {"rows": batch})
        total += len(batch)
    return total


# ---------------------------------------------------------------------------
# Population steps
# ---------------------------------------------------------------------------

def clear_database(driver):
    print("  Clearing existing data...")
    run_query(driver, "MATCH (n) DETACH DELETE n")
    print("  Database cleared.")


def create_constraints(driver):
    print("  Creating constraints and indexes...")
    constraints = [
        "CREATE CONSTRAINT company_ticker IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE",
        "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.expert_id IS UNIQUE",
        "CREATE CONSTRAINT cluster_name IF NOT EXISTS FOR (cl:Cluster) REQUIRE cl.name IS UNIQUE",
        "CREATE CONSTRAINT institution_name IF NOT EXISTS FOR (i:Institution) REQUIRE i.name IS UNIQUE",
        "CREATE CONSTRAINT regulation_name IF NOT EXISTS FOR (r:Regulation) REQUIRE r.name IS UNIQUE",
        "CREATE CONSTRAINT commodity_name IF NOT EXISTS FOR (cm:Commodity) REQUIRE cm.name IS UNIQUE",
        "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (co:Concept) REQUIRE co.name IS UNIQUE",
        "CREATE CONSTRAINT product_name IF NOT EXISTS FOR (pr:Product) REQUIRE pr.name IS UNIQUE",
        "CREATE CONSTRAINT facility_name IF NOT EXISTS FOR (f:Facility) REQUIRE f.name IS UNIQUE",
        "CREATE CONSTRAINT org_name IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
        "CREATE CONSTRAINT signal_id IF NOT EXISTS FOR (s:Signal) REQUIRE s.signal_id IS UNIQUE",
        "CREATE CONSTRAINT order_id IF NOT EXISTS FOR (ord:Order) REQUIRE ord.order_id IS UNIQUE",
    ]
    for c in constraints:
        try:
            run_query(driver, c)
        except Exception:
            pass
    print("  Constraints created.")


def create_companies(driver):
    print("  Creating Company nodes...")
    rows = []
    for ticker, data in STOCKS.items():
        rows.append({
            "ticker": ticker, "name": data["name"], "cluster": data["cluster"],
            "stock_type": data["stock_type"], "description": data["description"],
            "is_universe": True,
        })
    for ticker, data in SUPPLY_CHAIN_COMPANIES.items():
        rows.append({
            "ticker": ticker, "name": data["name"], "cluster": "SUPPLY_CHAIN",
            "stock_type": "supply_chain", "description": data["description"],
            "is_universe": False,
        })
    n = batch_create(driver,
        "UNWIND $rows AS row "
        "CREATE (c:Company {ticker: row.ticker, name: row.name, cluster: row.cluster, "
        "stock_type: row.stock_type, description: row.description, is_universe: row.is_universe})",
        rows)
    print(f"    → {n} companies")


def create_clusters(driver):
    print("  Creating Cluster nodes + MEMBER_OF edges...")
    for name, data in CLUSTERS.items():
        run_query(driver,
            "CREATE (cl:Cluster {name: $name, description: $desc})",
            {"name": name, "desc": data["description"]})
        for ticker in data["members"]:
            run_query(driver,
                "MATCH (c:Company {ticker: $ticker}), (cl:Cluster {name: $cluster}) "
                "CREATE (c)-[:MEMBER_OF]->(cl)",
                {"ticker": ticker, "cluster": name})
    print(f"    → {len(CLUSTERS)} clusters")


def create_institutions(driver):
    print("  Creating Institution nodes + OWNS_STAKE_IN edges...")
    for name, data in INSTITUTIONS.items():
        run_query(driver,
            "CREATE (i:Institution {name: $name, type: $type, description: $desc})",
            {"name": name, "type": data["type"], "desc": data["description"]})
        for ticker in data["holds"]:
            run_query(driver,
                "MATCH (i:Institution {name: $name}), (c:Company {ticker: $ticker}) "
                "CREATE (i)-[:OWNS_STAKE_IN]->(c)",
                {"name": name, "ticker": ticker})
    print(f"    → {len(INSTITUTIONS)} institutions")


def create_regulations(driver):
    print("  Creating Regulation nodes + REGULATES edges...")
    for name, data in REGULATIONS.items():
        run_query(driver,
            "CREATE (r:Regulation {name: $name, description: $desc, jurisdiction: $jur})",
            {"name": name, "desc": data["description"], "jur": data["jurisdiction"]})
        for ticker in data["affected"]:
            run_query(driver,
                "MATCH (r:Regulation {name: $name}), (c:Company {ticker: $ticker}) "
                "CREATE (r)-[:REGULATES]->(c)",
                {"name": name, "ticker": ticker})
    print(f"    → {len(REGULATIONS)} regulations")


def create_commodities(driver):
    print("  Creating Commodity nodes + SENSITIVE_TO edges...")
    for name, data in COMMODITIES.items():
        run_query(driver,
            "CREATE (cm:Commodity {name: $name, unit: $unit, price: $price, description: $desc})",
            {"name": name, "unit": data["unit"], "price": data["price"], "desc": data["description"]})
    # Link commodities to companies via supply chain triggers
    commodity_map = {
        "Natural Gas (Henry Hub)": "natural_gas_price",
        "Bitcoin": "bitcoin_price",
        "GPU Spot (H100)": "gpu_demand",
        "Electricity (NYC Zone J)": "nyc_power_demand",
    }
    for commodity_name, trigger in commodity_map.items():
        chain = SUPPLY_CHAIN.get(trigger, [])
        for ticker, relevance, desc in chain:
            run_query(driver,
                "MATCH (cm:Commodity {name: $commodity}), (c:Company {ticker: $ticker}) "
                "CREATE (c)-[:SENSITIVE_TO {relevance: $rel, mechanism: $desc}]->(cm)",
                {"commodity": commodity_name, "ticker": ticker, "rel": relevance, "desc": desc})
    print(f"    → {len(COMMODITIES)} commodities")


def create_concepts(driver):
    print("  Creating Concept nodes + THESIS_FOR edges...")
    for name, data in CONCEPTS.items():
        run_query(driver,
            "CREATE (co:Concept {name: $name, description: $desc})",
            {"name": name, "desc": data["description"]})
        for ticker in data["advocates"]:
            run_query(driver,
                "MATCH (co:Concept {name: $name}), (c:Company {ticker: $ticker}) "
                "CREATE (co)-[:THESIS_FOR {reasoning: 'Core thesis alignment'}]->(c)",
                {"name": name, "ticker": ticker})
    print(f"    → {len(CONCEPTS)} concepts")


def create_products(driver):
    print("  Creating Product nodes + PRODUCES edges...")
    for name, data in PRODUCTS.items():
        run_query(driver,
            "CREATE (pr:Product {name: $name, category: $cat, description: $desc})",
            {"name": name, "cat": data["category"], "desc": data["description"]})
        run_query(driver,
            "MATCH (c:Company {ticker: $ticker}), (pr:Product {name: $name}) "
            "CREATE (c)-[:PRODUCES]->(pr)",
            {"ticker": data["producer"], "name": name})
    print(f"    → {len(PRODUCTS)} products")


def create_facilities(driver):
    print("  Creating Facility nodes + OPERATES edges...")
    for name, data in FACILITIES.items():
        run_query(driver,
            "CREATE (f:Facility {name: $name, type: $type, location: $loc, "
            "capacity_mw: $cap, operator: $op, description: $desc})",
            {"name": name, "type": data["type"], "loc": data["location"],
             "cap": data["capacity_mw"], "op": data["operator"], "desc": data["description"]})
    print(f"    → {len(FACILITIES)} facilities")


def create_nyc_orgs(driver):
    print("  Creating Organization nodes...")
    for name, data in NYC_ORGS.items():
        run_query(driver,
            "CREATE (o:Organization {name: $name, description: $desc})",
            {"name": name, "desc": data["description"]})
    # Link orgs to relevant companies/commodities
    run_query(driver, """
        MATCH (o:Organization {name: 'Con Edison'}), (cm:Commodity {name: 'Electricity (NYC Zone J)'})
        CREATE (o)-[:SUPPLIES]->(cm)
    """)
    run_query(driver, """
        MATCH (o:Organization {name: 'NYISO'}), (cm:Commodity {name: 'Electricity (NYC Zone J)'})
        CREATE (o)-[:OPERATES_MARKET_FOR]->(cm)
    """)
    run_query(driver, """
        MATCH (o:Organization {name: 'Rise Light & Power'}), (f:Facility {name: 'Ravenswood Power Plant'})
        CREATE (o)-[:OPERATES]->(f)
    """)
    print(f"    → {len(NYC_ORGS)} organizations")


def create_supply_chain_edges(driver):
    print("  Creating supply chain edges...")
    count = 0
    # Upstream SUPPLIES edges
    for supplier, targets in UPSTREAM.items():
        for target in targets:
            run_query(driver,
                "MATCH (s:Company {ticker: $supplier}), (t:Company {ticker: $target}) "
                "CREATE (s)-[:SUPPLIES {direction: 'upstream'}]->(t)",
                {"supplier": supplier, "target": target})
            count += 1
    # Downstream CUSTOMER_OF edges
    for customer, sources in DOWNSTREAM.items():
        for source in sources:
            run_query(driver,
                "MATCH (c:Company {ticker: $customer}), (s:Company {ticker: $source}) "
                "CREATE (c)-[:CUSTOMER_OF]->(s)",
                {"customer": customer, "source": source})
            count += 1
    # Competitor edges
    for group in COMPETITOR_GROUPS:
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                run_query(driver,
                    "MATCH (a:Company {ticker: $a}), (b:Company {ticker: $b}) "
                    "CREATE (a)-[:COMPETES_WITH]->(b), (b)-[:COMPETES_WITH]->(a)",
                    {"a": a, "b": b})
                count += 2
    # Supply chain trigger edges (DRIVES)
    for trigger, chain in SUPPLY_CHAIN.items():
        for ticker, relevance, desc in chain:
            run_query(driver,
                "MATCH (c:Company {ticker: $ticker}) "
                "MERGE (t:Trigger {name: $trigger}) "
                "ON CREATE SET t.description = $desc "
                "CREATE (t)-[:DRIVES {relevance: $rel}]->(c)",
                {"ticker": ticker, "trigger": trigger, "rel": relevance, "desc": desc})
            count += 1
    print(f"    → {count} supply chain edges")


def create_experts(driver):
    print("  Creating Person (expert) nodes...")
    if not EXPERTS_CSV.exists():
        print("    WARNING: experts.csv not found, skipping")
        return 0

    rows = []
    with open(EXPERTS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            expert_id = row.get("Overall_Rank", "").strip()
            name = row.get("Name", "").strip()
            if not expert_id or not name:
                continue
            rows.append({
                "expert_id": expert_id,
                "name": name,
                "title": row.get("Title", ""),
                "organization": row.get("Organization", ""),
                "region": row.get("Region", ""),
                "category": row.get("Category", ""),
                "impact_score": float(row.get("Impact Score (1-10)", "5.0")),
                "expertise": row.get("Expertise/Justification", "")[:300],
            })

    n = batch_create(driver,
        "UNWIND $rows AS row "
        "CREATE (p:Person {expert_id: row.expert_id, name: row.name, title: row.title, "
        "organization: row.organization, region: row.region, category: row.category, "
        "impact_score: row.impact_score, expertise: row.expertise})",
        rows)
    print(f"    → {n} experts")

    # Create EXPERT_ON edges (expert → cluster based on category)
    edge_count = 0
    for row in rows:
        category = row["category"]
        for cat_key, tickers in CATEGORY_TO_TICKERS.items():
            if cat_key.lower() in category.lower():
                for ticker in tickers[:3]:  # top 3 to keep edges manageable
                    run_query(driver,
                        "MATCH (p:Person {expert_id: $eid}), (c:Company {ticker: $ticker}) "
                        "CREATE (p)-[:EXPERT_ON {impact_score: $score, category: $cat}]->(c)",
                        {"eid": row["expert_id"], "ticker": ticker,
                         "score": row["impact_score"], "cat": category})
                    edge_count += 1
                break  # first matching category only
    print(f"    → {edge_count} expert→company edges")
    return n


def create_signals_and_orders(driver):
    print("  Loading signals and orders from nexus.db...")
    if not NEXUS_DB.exists():
        print("    WARNING: nexus.db not found, skipping")
        return

    conn = sqlite3.connect(str(NEXUS_DB))
    conn.row_factory = sqlite3.Row

    # Raw signals → Signal nodes
    raw = conn.execute("""
        SELECT rs.id, rs.source, rs.expert_id, substr(rs.content, 1, 200) as snippet,
               rs.scraped_at,
               ps.sentiment, ps.sentiment_score, ps.relevance_score, substr(ps.summary, 1, 200) as summary
        FROM raw_signals rs
        LEFT JOIN processed_signals ps ON ps.raw_signal_id = rs.id
    """).fetchall()

    signal_rows = []
    for r in raw:
        signal_rows.append({
            "signal_id": f"sig-{r['id']}",
            "source_type": r["source"] or "unknown",
            "expert_id": r["expert_id"] or "",
            "snippet": r["snippet"] or "",
            "summary": r["summary"] or "",
            "sentiment": r["sentiment"] or "neutral",
            "sentiment_score": r["sentiment_score"] or 0.0,
            "relevance_score": r["relevance_score"] or 0.0,
            "scraped_at": r["scraped_at"] or "",
        })

    n = batch_create(driver,
        "UNWIND $rows AS row "
        "CREATE (s:Signal {signal_id: row.signal_id, source_type: row.source_type, "
        "snippet: row.snippet, summary: row.summary, sentiment: row.sentiment, "
        "sentiment_score: row.sentiment_score, relevance_score: row.relevance_score, "
        "scraped_at: row.scraped_at})",
        signal_rows)
    print(f"    → {n} signals")

    # Signal → Person (AUTHORED_BY) edges
    authored_count = 0
    for row in signal_rows:
        if row["expert_id"]:
            # Try to find expert by expert_id match
            run_query(driver,
                "MATCH (s:Signal {signal_id: $sid}), (p:Person) "
                "WHERE p.expert_id CONTAINS $eid OR toLower(p.name) CONTAINS toLower($eid) "
                "WITH s, p LIMIT 1 "
                "CREATE (s)-[:AUTHORED_BY]->(p)",
                {"sid": row["signal_id"], "eid": row["expert_id"]})
            authored_count += 1
    print(f"    → {authored_count} signal→expert edges")

    # Trade signals → GENERATED_TRADE edges
    trades = conn.execute("""
        SELECT id, raw_signal_id, expert_id, symbol, direction, composite_score, confidence
        FROM trade_signals
    """).fetchall()

    trade_count = 0
    for t in trades:
        sig_id = f"sig-{t['raw_signal_id']}" if t["raw_signal_id"] else None
        if sig_id:
            run_query(driver,
                "MATCH (s:Signal {signal_id: $sid}), (c:Company {ticker: $ticker}) "
                "CREATE (s)-[:GENERATED_TRADE {direction: $dir, composite_score: $score, "
                "confidence: $conf}]->(c)",
                {"sid": sig_id, "ticker": t["symbol"], "dir": t["direction"],
                 "score": t["composite_score"], "conf": t["confidence"]})
            trade_count += 1
    print(f"    → {trade_count} trade signal edges")

    # Orders → Order nodes
    orders = conn.execute("""
        SELECT id, symbol, side, quantity, filled_price, status, kelly_fraction,
               position_size_usd, realized_pnl, is_paper, created_at
        FROM orders
    """).fetchall()

    order_rows = []
    for o in orders:
        order_rows.append({
            "order_id": f"ord-{o['id']}",
            "symbol": o["symbol"],
            "side": o["side"],
            "quantity": o["quantity"],
            "price": o["filled_price"] or 0,
            "status": o["status"],
            "kelly_fraction": o["kelly_fraction"] or 0,
            "position_size_usd": o["position_size_usd"] or 0,
            "realized_pnl": o["realized_pnl"] or 0,
            "is_paper": bool(o["is_paper"]),
            "created_at": o["created_at"] or "",
        })

    n = batch_create(driver,
        "UNWIND $rows AS row "
        "CREATE (o:Order {order_id: row.order_id, side: row.side, quantity: row.quantity, "
        "price: row.price, status: row.status, kelly_fraction: row.kelly_fraction, "
        "position_size_usd: row.position_size_usd, realized_pnl: row.realized_pnl, "
        "is_paper: row.is_paper, created_at: row.created_at})",
        order_rows)
    print(f"    → {n} orders")

    # Order → Company edges
    for row in order_rows:
        sym = orders[int(row["order_id"].split("-")[1]) - 1]["symbol"]
        run_query(driver,
            "MATCH (o:Order {order_id: $oid}), (c:Company {ticker: $ticker}) "
            "CREATE (o)-[:EXECUTED_ON]->(c)",
            {"oid": row["order_id"], "ticker": sym})

    conn.close()
    print(f"    → {len(order_rows)} order→company edges")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def print_stats(driver):
    print("\n" + "=" * 60)
    print("GRAPH STATISTICS")
    print("=" * 60)

    # Node counts by label
    result = run_query(driver,
        "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC")
    total_nodes = 0
    for r in result:
        print(f"  {r['label']:20s} {r['count']:>6d}")
        total_nodes += r["count"]
    print(f"  {'TOTAL':20s} {total_nodes:>6d}")

    # Edge counts by type
    print()
    result = run_query(driver,
        "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC")
    total_edges = 0
    for r in result:
        print(f"  {r['type']:25s} {r['count']:>6d}")
        total_edges += r["count"]
    print(f"  {'TOTAL':25s} {total_edges:>6d}")
    print()


def run_sample_queries(driver):
    print("=" * 60)
    print("SAMPLE QUERIES")
    print("=" * 60)

    # 1. Leopold's fund holdings
    print("\n1. What companies does Leopold's fund own?")
    result = run_query(driver,
        "MATCH (i:Institution {name: 'Situational Awareness LP'})-[:OWNS_STAKE_IN]->(c:Company) "
        "RETURN c.ticker AS ticker, c.name AS name, c.description AS desc")
    for r in result:
        print(f"   {r['ticker']:6s} {r['name']}")

    # 2. Supply chain path: GPU demand → EQT
    print("\n2. Supply chain: GPU demand → natural gas")
    result = run_query(driver,
        "MATCH path = (t:Trigger {name: 'gpu_demand'})-[:DRIVES]->(c:Company) "
        "RETURN c.ticker AS ticker, c.name AS name "
        "ORDER BY c.ticker")
    for r in result:
        print(f"   GPU demand → {r['ticker']} ({r['name']})")

    # 3. High-impact experts
    print("\n3. Top experts (impact_score >= 9.0)")
    result = run_query(driver,
        "MATCH (p:Person) WHERE p.impact_score >= 9.0 "
        "RETURN p.name AS name, p.organization AS org, p.impact_score AS score "
        "ORDER BY score DESC LIMIT 10")
    for r in result:
        print(f"   {r['score']:.1f}  {r['name']:30s}  {r['org']}")

    # 4. NYC facilities
    print("\n4. NYC metro facilities (by capacity)")
    result = run_query(driver,
        "MATCH (f:Facility) "
        "RETURN f.name AS name, f.type AS type, f.capacity_mw AS mw, f.location AS loc "
        "ORDER BY mw DESC LIMIT 8")
    for r in result:
        print(f"   {r['mw']:>6d} MW  {r['name']:40s}  ({r['loc']})")

    # 5. Most connected companies
    print("\n5. Most connected companies")
    result = run_query(driver,
        "MATCH (c:Company)-[r]-() "
        "RETURN c.ticker AS ticker, c.name AS name, count(r) AS connections "
        "ORDER BY connections DESC LIMIT 10")
    for r in result:
        print(f"   {r['connections']:>4d}  {r['ticker']:6s}  {r['name']}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  DC & Energy Nexus — Neo4j Graph Population             ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    uri, user, password = get_neo4j_config()
    print(f"Connecting to {uri}...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("Connected!\n")

    print("Step 1: Clear database + create constraints")
    clear_database(driver)
    create_constraints(driver)

    print("\nStep 2: Create nodes")
    create_companies(driver)
    create_clusters(driver)
    create_institutions(driver)
    create_regulations(driver)
    create_commodities(driver)
    create_concepts(driver)
    create_products(driver)
    create_facilities(driver)
    create_nyc_orgs(driver)

    print("\nStep 3: Create edges")
    create_supply_chain_edges(driver)

    print("\nStep 4: Load experts from CSV")
    create_experts(driver)

    print("\nStep 5: Load signals + orders from nexus.db")
    create_signals_and_orders(driver)

    # Stats and verification
    print_stats(driver)
    run_sample_queries(driver)

    driver.close()
    print("Done! Graph populated successfully.")


if __name__ == "__main__":
    main()
