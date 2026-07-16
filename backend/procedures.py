"""
Dental procedure catalog with CDT codes and radiograph requirements.
Radiograph legend:
  PA   - Periapical
  BW   - Bitewing
  FMX  - Full-mouth series
  PANO - Panoramic
  CBCT - Cone-Beam CT
  PHOTO - Intraoral photograph (as adjunct)
"""

PROCEDURES = [
    # Crowns / Restorative
    {
        "code": "D2740",
        "name": "Crown - porcelain/ceramic",
        "category": "Crown",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW", "PA (post-prep)"],
            "note": "Most carriers require a pre-op PA showing decay, fracture, or prior restoration failure."
        }
    },
    {
        "code": "D2750",
        "name": "Crown - porcelain fused to metal",
        "category": "Crown",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW", "PA (post-prep)"],
            "note": "Include narrative describing structural loss and reason porcelain-fused-to-metal was chosen."
        }
    },
    {
        "code": "D2950",
        "name": "Core buildup, including any pins",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op or post-prep)"],
            "recommended": ["Intraoral photo of prepped tooth"],
            "note": "Must document that >50% of coronal tooth structure is missing to justify buildup."
        }
    },
    {
        "code": "D2543",
        "name": "Onlay - metallic - three surfaces",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW"],
            "note": "Document cuspal involvement."
        }
    },
    {
        "code": "D2644",
        "name": "Inlay - porcelain/ceramic - four+ surfaces",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW"],
            "note": ""
        }
    },
    # Endodontics
    {
        "code": "D3310",
        "name": "Endodontic therapy, anterior tooth (excluding final restoration)",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)", "PA (working length)", "PA (post-op / final fill)"],
            "recommended": [],
            "note": "All three PA images should be submitted with the claim."
        }
    },
    {
        "code": "D3320",
        "name": "Endodontic therapy, premolar tooth",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)", "PA (working length)", "PA (post-op)"],
            "recommended": [],
            "note": ""
        }
    },
    {
        "code": "D3330",
        "name": "Endodontic therapy, molar tooth",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)", "PA (working length)", "PA (post-op)"],
            "recommended": ["CBCT if calcified canals or unusual anatomy"],
            "note": ""
        }
    },
    # Extractions
    {
        "code": "D7140",
        "name": "Extraction, erupted tooth or exposed root",
        "category": "Extraction",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": [],
            "note": "Document reason: non-restorable caries, fracture, periodontal, orthodontic."
        }
    },
    {
        "code": "D7210",
        "name": "Surgical removal of erupted tooth (requires elevation of flap or sectioning)",
        "category": "Extraction",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["PANO"],
            "note": "Narrative must state that flap and/or sectioning was required."
        }
    },
    {
        "code": "D7240",
        "name": "Removal of impacted tooth - completely bony",
        "category": "Extraction",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PANO or CBCT"],
            "recommended": ["PA"],
            "note": "Must show full bony impaction."
        }
    },
    # Periodontics
    {
        "code": "D4341",
        "name": "Periodontal scaling & root planing - 4+ teeth per quadrant",
        "category": "Periodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PAs with BWs (within 24 months)"],
            "recommended": [],
            "note": "Must submit full periodontal chart with pocket depths and bone loss evidence."
        }
    },
    {
        "code": "D4342",
        "name": "Periodontal scaling & root planing - 1-3 teeth per quadrant",
        "category": "Periodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["PA or BW showing bone loss"],
            "recommended": [],
            "note": "Perio chart with pocket depths for the specific teeth."
        }
    },
    {
        "code": "D4910",
        "name": "Periodontal maintenance",
        "category": "Periodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["Current BWs (yearly)"],
            "note": "Prior SRP within last 3 years must be documented."
        }
    },
    # Implants
    {
        "code": "D6010",
        "name": "Surgical placement of implant body: endosteal implant",
        "category": "Implant",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)", "PANO", "PA (post-op)"],
            "recommended": ["CBCT"],
            "note": "Document reason for tooth loss and time edentulous."
        }
    },
    {
        "code": "D6057",
        "name": "Custom fabricated abutment - includes modification and placement",
        "category": "Implant",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of implant with abutment"],
            "recommended": [],
            "note": ""
        }
    },
    {
        "code": "D6058",
        "name": "Abutment supported porcelain/ceramic crown",
        "category": "Implant",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of seated crown"],
            "recommended": [],
            "note": ""
        }
    },
    # Bridges
    {
        "code": "D6240",
        "name": "Pontic - porcelain fused to high noble metal",
        "category": "Bridge",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of abutments (pre-op)"],
            "recommended": [],
            "note": "Document date of tooth loss for missing tooth clause."
        }
    },
    # Grafts
    {
        "code": "D7953",
        "name": "Bone replacement graft for ridge preservation - per site",
        "category": "Surgical",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["CBCT"],
            "note": "Document ridge defect and implant planning."
        }
    },
    {
        "code": "D7952",
        "name": "Sinus augmentation via lateral open approach",
        "category": "Surgical",
        "requires_tooth": False,
        "radiographs": {
            "required": ["CBCT (pre-op)"],
            "recommended": ["PANO"],
            "note": "Document residual bone height."
        }
    },
    # Occlusal guards
    {
        "code": "D9944",
        "name": "Occlusal guard - hard appliance, full arch",
        "category": "Occlusal Guard",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["Intraoral photos of wear facets/abfractions"],
            "note": "Document bruxism signs; carrier may exclude if TMD-only."
        }
    },
    {
        "code": "D9945",
        "name": "Occlusal guard - soft appliance, full arch",
        "category": "Occlusal Guard",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["Intraoral photos of wear facets"],
            "note": ""
        }
    },
]


def get_procedure(code: str):
    for p in PROCEDURES:
        if p["code"] == code:
            return p
    return None
