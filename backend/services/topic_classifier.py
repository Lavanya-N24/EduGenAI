"""
EduGenAI - Smart Topic Classifier

Categorizes any educational topic into a video format:

  ANIMATED    -> Full biological / process animation (blockchain, photosynthesis, solar system, DNA, physics)
  DOCUMENTARY -> Educational slide with text + authentic photo (history, biography, geography)
  SCIENCE     -> Generic science (chemistry equations, physics formulas)

Used at the very start of generate_video() to decide the rendering strategy.
"""

from __future__ import annotations

import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

TopicCategory = Literal["ANIMATED", "DOCUMENTARY", "SCIENCE"]

_ANIMATED_KEYWORDS = {
    "photosynthesis", "chlorophyll", "chloroplast", "stomata", "xylem", "phloem",
    "plant", "plants", "leaf", "leaves", "roots", "seed", "germination", "botany",
    "algae", "moss", "fern", "tree", "flower", "pollination",
    "chemical reaction", "molecule", "atom", "compound", "periodic table",
    "acid", "base", "oxidation", "reduction", "electrolysis", "titration",
    "covalent", "ionic", "combustion", "respiration", "fermentation",
    "newton", "force", "momentum", "velocity", "acceleration", "projectile",
    "wave", "frequency", "wavelength", "electromagnetic", "refraction", "diffraction",
    "thermodynamics", "entropy", "heat", "conduction", "convection", "radiation",
    "nuclear", "radioactive", "quantum", "relativity", "electricity", "circuit",
    "dna", "rna", "gene", "genetics", "chromosome", "mitosis", "meiosis",
    "cell", "cells", "nucleus", "membrane", "protein", "transcription", "translation",
    "evolution", "mutation", "heredity",
    "solar", "planet", "orbit", "moon", "sun", "galaxy", "universe",
    "asteroid", "comet", "black hole", "nebula", "star", "constellation",
    "big bang", "telescope", "gravity", "space", "atmosphere",
    "volcano", "earthquake", "tectonic", "erosion", "weather", "climate",
    "water cycle", "carbon cycle", "nitrogen cycle", "food chain", "ecosystem",
    "water", "rain", "evaporation", "condensation",
    "blockchain", "bitcoin", "ethereum", "crypto", "cryptocurrency",
    "distributed ledger", "smart contract", "web3", "mining", "consensus",
    "algorithm", "sorting", "fibonacci", "neural", "machine learning",
}

_DOCUMENTARY_KEYWORDS = {
    "history", "ancient", "medieval", "empire", "civilization", "dynasty",
    "war", "battle", "revolution", "independence", "partition", "treaty",
    "colonialism", "imperialism", "renaissance", "industrial revolution",
    "biography", "leader", "king", "queen", "president", "prime minister",
    "emperor", "ruler", "founder",
    "shivaji", "maharaj", "mughal", "tipu", "sultan", "ashoka", "akbar", "gandhi",
    "nehru", "ambedkar", "bose", "rani", "chandragupta", "maratha", "rajput",
    "napoleon", "caesar", "cleopatra", "churchill", "washington", "lincoln",
    "geography", "country", "continent", "capital", "map", "river", "mountain",
    "himalaya", "amazon", "nile", "sahara",
    "culture", "heritage", "monument", "temple", "palace", "fort", "architecture",
    "religion", "festival", "tradition", "mythology", "folklore",
    "economy", "government", "democracy", "constitution", "law", "rights",
}


def _has_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    """Check if any keyword is in text as a whole word or phrase."""
    for kw in keywords:
        if " " in kw or "-" in kw:
            if kw in text:
                return True
        else:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                return True
    return False


def classify_topic(topic: str) -> dict:
    """Classify any educational topic and return rendering strategy."""
    text = topic.lower().strip()
    words = set(re.findall(r"[a-z0-9_]+", text))

    doc_matches = _DOCUMENTARY_KEYWORDS & words
    doc_phrase_match = any(phrase in text for phrase in (
        "world war", "civil war", "cold war", "life of", "the story of",
        "biography of", "history of", "map of", "culture of",
    ))

    if doc_matches or doc_phrase_match:
        logger.info("DOCUMENTARY topic: %s", topic)
        return {
            "category": "DOCUMENTARY",
            "motion": "documentary",
            "animation_style": "Educational Slide with Authentic Photo",
            "use_images": True,
            "equation": None,
        }

    # ── Blockchain / Crypto / Web3 ──
    if _has_keyword(text, (
        "blockchain", "bitcoin", "ethereum", "crypto", "cryptocurrency",
        "smart contract", "smart contracts", "distributed ledger", "web3",
        "mining", "consensus", "decentralized", "proof of work", "proof of stake",
        "nft", "tokenomics", "hash function", "sha-256", "cryptographic",
    )):
        return {
            "category": "ANIMATED",
            "motion": "blockchain",
            "animation_style": "Decentralized Blockchain & Distributed Network Animation",
            "use_images": False,
            "equation": "SHA-256(Block Data + Nonce) < Target Hash",
        }

    # ── Astronomy / Space ──
    if _has_keyword(text, (
        "solar system", "planet", "galaxy", "black hole", "orbit", "nebula",
        "comet", "asteroid", "telescope", "star", "universe", "big bang",
        "space exploration", "cosmos", "astronomy",
    )):
        return {
            "category": "ANIMATED",
            "motion": "space",
            "animation_style": "Cinematic Space & Orbital Animation",
            "use_images": False,
            "equation": "F = G * m1 * m2 / r^2  (Newton's Gravitation)",
        }

    # ── Photosynthesis / Botany ──
    if _has_keyword(text, (
        "photosynthesis", "chlorophyll", "chloroplast", "plant", "plants",
        "leaf", "leaves", "stomata", "botany", "algae", "food chain",
    )):
        return {
            "category": "ANIMATED",
            "motion": "photosynthesis",
            "animation_style": "Biological Process Animation (Sunlight + CO2 + O2)",
            "use_images": False,
            "equation": "6CO2 + 6H2O + Sunlight -> C6H12O6 + 6O2",
        }

    # ── Water Cycle / Earth Science ──
    if _has_keyword(text, (
        "water cycle", "water", "rain", "evaporation", "condensation",
        "precipitation", "weather", "climate", "hydrological",
    )):
        return {
            "category": "ANIMATED",
            "motion": "photosynthesis",
            "animation_style": "Earth Science & Water Cycle Animation",
            "use_images": False,
            "equation": "Evaporation -> Condensation -> Precipitation  (Water Cycle)",
        }

    # ── Cell Biology / DNA / Genetics ──
    if _has_keyword(text, (
        "dna", "rna", "gene", "genetics", "chromosome", "mitosis",
        "meiosis", "cell", "heredity", "evolution", "mutation", "protein",
    )):
        return {
            "category": "ANIMATED",
            "motion": "dna",
            "animation_style": "DNA Double Helix & Cell Biology Animation",
            "use_images": False,
            "equation": "DNA -> mRNA -> Protein  (Central Dogma)",
        }

    # ── Human Anatomy ──
    if _has_keyword(text, (
        "heart", "blood", "circulatory", "digestive", "respiratory",
        "nervous system", "brain", "kidney", "lungs", "anatomy", "organ",
        "muscle", "bone", "skeleton",
    )):
        return {
            "category": "ANIMATED",
            "motion": "dna",
            "animation_style": "Human Anatomy Animation",
            "use_images": False,
            "equation": None,
        }

    # ── Chemistry ──
    if _has_keyword(text, (
        "periodic table", "element", "chemical reaction", "acid", "base",
        "molecule", "atom", "compound", "oxidation", "combustion", "titration", "chemistry",
    )):
        return {
            "category": "ANIMATED",
            "motion": "photosynthesis",
            "animation_style": "Chemistry & Molecular Reaction Animation",
            "use_images": False,
            "equation": None,
        }

    # ── Physics / Mathematics ──
    if _has_keyword(text, (
        "newton", "force", "momentum", "velocity", "acceleration", "quantum",
        "relativity", "wave", "electricity", "circuit", "thermodynamics",
        "optics", "gravity", "friction", "physics", "mathematics", "calculus", "algebra",
    )):
        return {
            "category": "ANIMATED",
            "motion": "space",
            "animation_style": "Physics & Mathematics Animation",
            "use_images": False,
            "equation": None,
        }

    # ── Volcano / Earthquake / Earth ──
    if _has_keyword(text, (
        "volcano", "earthquake", "tectonic", "erosion", "ecosystem",
        "food chain", "nitrogen cycle", "carbon cycle",
    )):
        return {
            "category": "ANIMATED",
            "motion": "photosynthesis",
            "animation_style": "Earth Science Animation",
            "use_images": False,
            "equation": None,
        }

    # ── Computer Science / AI / Circuits ──
    if _has_keyword(text, (
        "algorithm", "neural network", "machine learning", "deep learning", "ai",
        "computer science", "programming", "data structure", "sorting", "cpu", "chip", "circuits",
    )):
        return {
            "category": "ANIMATED",
            "motion": "circuits",
            "animation_style": "Computer Science & Neural Circuits Diagram",
            "use_images": False,
            "equation": None,
        }

    # ── General ANIMATED keyword match ──
    anim_matches = _ANIMATED_KEYWORDS & words
    if anim_matches:
        logger.info("ANIMATED (Science) topic: %s", topic)
        return {
            "category": "ANIMATED",
            "motion": "photosynthesis",
            "animation_style": "Scientific Process Animation",
            "use_images": False,
            "equation": None,
        }

    # ── Default: DOCUMENTARY ──
    logger.info("DOCUMENTARY (default) topic: %s", topic)
    return {
        "category": "DOCUMENTARY",
        "motion": "documentary",
        "animation_style": "Educational Slide with Authentic Photo",
        "use_images": True,
        "equation": None,
    }


def get_scene_motion(scene: dict, topic_category: str, topic_motion: str, scene_idx: int = 0, total_scenes: int = 1) -> str:
    """
    Get the visual_animation motion string for a single scene.
    DOCUMENTARY topics always use 'documentary'.
    ANIMATED topics route by scene content to ensure every scene has a unique, focused visual.
    """
    if topic_category == "DOCUMENTARY":
        return "documentary"

    text = " ".join(
        str(scene.get(k, ""))
        for k in ("title", "narration", "visual_description", "visual_prompt")
    ).lower()

    # ── Blockchain Stage Routing ──
    if topic_motion in ("blockchain", "blockchain_network", "crypto", "bitcoin", "ethereum", "web3", "ledger"):
        # 1. Mining & Proof of Work / Consensus
        if _has_keyword(text, ("mine", "mining", "proof of work", "pow", "pos", "consensus", "validator", "nonce", "target", "solve", "reward")):
            return "blockchain_mining"
        # 2. Smart Contracts & Decentralized Execution
        elif _has_keyword(text, ("contract", "smart contract", "smart contracts", "code", "execute", "condition", "dapp", "ethereum", "agreement", "solidity")):
            return "blockchain_smart_contracts"
        # 3. Distributed P2P Network / Nodes / Introduction / Bank comparison
        elif _has_keyword(text, ("p2p", "peer", "node", "nodes", "decentralized", "distributed", "network", "bank", "centralized", "trustless", "intermediary", "middleman", "introduction", "overview")):
            return "blockchain_network"
        # 4. Blocks & Cryptographic Hash Chain
        elif _has_keyword(text, ("block", "blocks", "hash", "hashes", "sha-256", "sha256", "cryptography", "chain", "immutable", "tamper")):
            return "blockchain_blocks"

        # Fallback progression by scene index to guarantee every scene looks unique
        cycle = ["blockchain_network", "blockchain_blocks", "blockchain_mining", "blockchain_smart_contracts"]
        return cycle[scene_idx % len(cycle)]

    # ── Biology / Photosynthesis Stage Routing ──
    if topic_motion in ("photosynthesis", "photo_sunlight", "botany", "plant"):
        # The CORRECT pedagogical order of photosynthesis for video scenes:
        #   Scene 1 → Sunlight / Introduction
        #   Scene 2 → Water absorption through roots
        #   Scene 3 → CO2 intake through stomata
        #   Scene 4 → Inside the chloroplast (chemical conversion)
        #   Scene 5 → Oxygen release + glucose output
        #   Scene 6+ → Chemical equation / summary

        # Priority 1: Force first scene to ALWAYS be sunlight (introduction)
        if scene_idx == 0:
            return "plant_sunlight"

        # Priority 2: Last scene or "equation/summary" scene → equation overlay
        if scene_idx >= total_scenes - 1 or any(k in text for k in (
            "equation", "summary", "overall", "formula", "chemical formula",
            "chemical reaction", "reaction formula", "conclusion", "recap",
        )):
            return "photo_equation"

        # Priority 3: Keyword routing for middle scenes
        # Roots / Water — scene 2
        if any(k in text for k in ("root", "roots", "water", "h2o", "soil", "xylem",
                                    "drink", "absorb water", "ground", "stem")):
            return "photo_roots"
        # Stomata / CO2 intake — scene 3
        if any(k in text for k in ("stomata", "stoma", "pore", "pores", "underside",
                                    "guard cell", "co2", "carbon", "dioxide", "intake", "air")):
            return "photo_stomata"
        # Chloroplast / internal chemistry — scene 4
        if any(k in text for k in ("chloroplast", "chlorophyll", "thylakoid", "grana",
                                    "calvin", "chemical conversion", "inside the leaf", "green")):
            return "photo_chloroplast"
        # Oxygen / Glucose output — scene 5
        if any(k in text for k in ("oxygen", "glucose", "sugar", "o2", "c6h12o6",
                                    "release", "emit", "stored", "produce oxygen", "output")):
            return "photo_oxygen"
        # Sunlight keywords in any middle scene
        if any(k in text for k in ("sun", "sunlight", "photon", "photons", "solar",
                                    "light energy", "solar energy", "absorb sunlight", "light")):
            return "plant_sunlight"

        # Priority 4: Index-based strict cycle (ensures no two adjacent scenes look the same)
        cycle = ["plant_sunlight", "photo_roots", "photo_stomata",
                 "photo_chloroplast", "photo_oxygen", "photo_equation"]
        return cycle[scene_idx % len(cycle)]

    # ── DNA / Genetics ──
    if any(k in text for k in ("dna", "gene", "chromosome", "cell", "mitosis")):
        return "dna"

    # ── Astronomy / Space ──
    if any(k in text for k in ("space", "planet", "orbit", "galaxy", "star", "moon", "solar")):
        return "space"

    # ── Computer Science / Circuits ──
    if any(k in text for k in ("circuit", "cpu", "chip", "neural", "binary", "logic", "code")):
        return "circuits"

    return topic_motion
