"""
Dental procedure catalog with CDT codes and radiograph requirements.
Radiograph legend:
  PA    - Periapical
  BW    - Bitewing
  FMX   - Full-mouth series
  PANO  - Panoramic
  CBCT  - Cone-Beam CT
  PHOTO - Intraoral photograph (as adjunct)
"""

PROCEDURES = [
    # ------------------------------------------------------------------
    # Diagnostic (D0xxx)
    # ------------------------------------------------------------------
    {
        "code": "D0140",
        "name": "Limited oral evaluation - problem focused",
        "category": "Diagnostic",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["PA of area of concern"],
            "note": "Document the specific problem, patient's chief complaint, and findings. Not billable same day as D0120/D0150 by most carriers.",
        },
    },
    {
        "code": "D0150",
        "name": "Comprehensive oral evaluation - new or established patient",
        "category": "Diagnostic",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["FMX or PANO+BW"],
            "note": "Once per provider per lifetime for most carriers. Include perio charting, oral cancer screening, treatment plan.",
        },
    },
    {
        "code": "D0180",
        "name": "Comprehensive periodontal evaluation",
        "category": "Diagnostic",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["FMX or PANO+BW"],
            "note": "For patients with signs or symptoms of periodontal disease. Document probing depths, bleeding on probing, mobility, furcation involvement.",
        },
    },
    {
        "code": "D0210",
        "name": "Intraoral - complete series (FMX)",
        "category": "Diagnostic",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Usually limited to once every 3-5 years by carrier. Document diagnostic necessity if repeated sooner.",
        },
    },
    {
        "code": "D0220",
        "name": "Intraoral - periapical, first radiographic image",
        "category": "Diagnostic",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Bill with D0230 for each additional PA taken same visit.",
        },
    },
    {
        "code": "D0270",
        "name": "Bitewing - single radiographic image",
        "category": "Diagnostic",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "For BW series bill D0272 (two), D0273 (three), or D0274 (four).",
        },
    },
    {
        "code": "D0330",
        "name": "Panoramic radiographic image",
        "category": "Diagnostic",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Frequency limit usually 3-5 years. Not billable same day as FMX by most carriers.",
        },
    },
    {
        "code": "D0350",
        "name": "2D oral/facial photographic image obtained intra-orally or extra-orally",
        "category": "Diagnostic",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Intraoral photos as diagnostic adjunct. Attach photo file with claim; document why the photo was clinically necessary (e.g., wear, fracture, soft tissue lesion).",
        },
    },

    # ------------------------------------------------------------------
    # Preventive (D1xxx)
    # ------------------------------------------------------------------
    {
        "code": "D1110",
        "name": "Prophylaxis - adult",
        "category": "Preventive",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Age 14+. Typical carrier limit: 2 per calendar year. Not billable when patient has active periodontal disease (see D4341/D4342/D4910).",
        },
    },
    {
        "code": "D1120",
        "name": "Prophylaxis - child",
        "category": "Preventive",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Age 13 and under. Typical carrier limit: 2 per calendar year.",
        },
    },
    {
        "code": "D1206",
        "name": "Topical application of fluoride varnish",
        "category": "Preventive",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Frequency typically 2 per year, age-limited by carrier (often under age 14-19). Document caries risk for adult claims.",
        },
    },
    {
        "code": "D1310",
        "name": "Nutritional counseling for control of dental disease",
        "category": "Preventive",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Document time spent, patient's caries or erosion risk factors discussed, and specific dietary recommendations given. Often not a covered benefit; expect frequent denials.",
        },
    },
    {
        "code": "D1351",
        "name": "Sealant - per tooth",
        "category": "Preventive",
        "requires_tooth": True,
        "radiographs": {
            "required": [],
            "recommended": ["BW or PHOTO showing deep pits/fissures"],
            "note": "Usually covered on permanent 1st and 2nd molars for kids. Include tooth number, surface treated (typically occlusal).",
        },
    },

    # ------------------------------------------------------------------
    # Restorative - Direct fillings (D2xxx)
    # ------------------------------------------------------------------
    {
        "code": "D2140",
        "name": "Amalgam - one surface, primary or permanent",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["BW or PA showing caries"],
            "recommended": [],
            "note": "Document surface, extent of caries.",
        },
    },
    {
        "code": "D2150",
        "name": "Amalgam - two surfaces, primary or permanent",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["BW or PA showing caries"],
            "recommended": [],
            "note": "Document both surfaces, e.g., MO or DO.",
        },
    },
    {
        "code": "D2160",
        "name": "Amalgam - three surfaces",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["BW or PA showing caries"],
            "recommended": [],
            "note": "Document all three surfaces, e.g., MOD.",
        },
    },
    {
        "code": "D2161",
        "name": "Amalgam - four or more surfaces",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["BW or PA showing caries"],
            "recommended": ["PHOTO"],
            "note": "Document all surfaces treated and cusp involvement if any.",
        },
    },
    {
        "code": "D2330",
        "name": "Resin-based composite - one surface, anterior",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing caries or fracture"],
            "recommended": [],
            "note": "Document surface treated (F, L, M, D, or I) and caries or fracture etiology.",
        },
    },
    {
        "code": "D2331",
        "name": "Resin-based composite - two surfaces, anterior",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing caries or fracture"],
            "recommended": [],
            "note": "Document both surfaces (e.g., MI or DI).",
        },
    },
    {
        "code": "D2332",
        "name": "Resin-based composite - three surfaces, anterior",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing caries or fracture"],
            "recommended": [],
            "note": "Document all three surfaces.",
        },
    },
    {
        "code": "D2335",
        "name": "Resin-based composite - four or more surfaces or involving incisal angle, anterior",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing caries or fracture"],
            "recommended": ["PHOTO"],
            "note": "Document incisal angle involvement or number of surfaces.",
        },
    },
    {
        "code": "D2391",
        "name": "Resin-based composite - one surface, posterior",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["BW or PA showing caries"],
            "recommended": [],
            "note": "Document surface treated. Carrier may downgrade to amalgam equivalent (D2140) on posterior teeth.",
        },
    },
    {
        "code": "D2392",
        "name": "Resin-based composite - two surfaces, posterior",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["BW or PA showing caries"],
            "recommended": [],
            "note": "Document both surfaces. Carrier may downgrade to amalgam equivalent (D2150).",
        },
    },
    {
        "code": "D2393",
        "name": "Resin-based composite - three surfaces, posterior",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["BW or PA showing caries"],
            "recommended": [],
            "note": "Document all three surfaces. Carrier may downgrade to amalgam equivalent (D2160).",
        },
    },
    {
        "code": "D2394",
        "name": "Resin-based composite - four or more surfaces, posterior",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["BW or PA showing caries"],
            "recommended": ["PHOTO"],
            "note": "Document all surfaces and cusp involvement.",
        },
    },

    # ------------------------------------------------------------------
    # Restorative - Indirect + core (D2xxx)
    # ------------------------------------------------------------------
    {
        "code": "D2543",
        "name": "Onlay - metallic - three surfaces",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW"],
            "note": "Document cusp coverage rationale; note if replacing failed restoration.",
        },
    },
    {
        "code": "D2644",
        "name": "Onlay - porcelain/ceramic - four or more surfaces",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW", "PHOTO"],
            "note": "Common denial: 'less costly alternative'. Justify porcelain with esthetic-zone or metal allergy documentation if applicable.",
        },
    },
    {
        "code": "D2950",
        "name": "Core buildup, including any pins",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op or post-prep)"],
            "recommended": ["PHOTO of prepped tooth"],
            "note": "Must document that >50% of coronal tooth structure is missing to justify buildup.",
        },
    },
    {
        "code": "D2952",
        "name": "Post and core in addition to crown, indirectly fabricated",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing endodontic obturation and remaining tooth structure"],
            "recommended": ["PHOTO of prepped tooth"],
            "note": "Endodontically treated tooth. Document need for post retention due to insufficient coronal tooth structure.",
        },
    },
    {
        "code": "D2954",
        "name": "Prefabricated post and core in addition to crown",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing endodontic obturation"],
            "recommended": ["PHOTO of prepped tooth"],
            "note": "Endodontically treated tooth requiring post retention.",
        },
    },
    {
        "code": "D2999",
        "name": "Unspecified restorative procedure, by report",
        "category": "Restorative",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of tooth"],
            "recommended": ["PHOTO"],
            "note": "Use only when no other CDT code applies. A detailed narrative is REQUIRED - describe exactly what was done, materials used, and why a specific code doesn't fit. High denial rate without thorough documentation.",
        },
    },

    # ------------------------------------------------------------------
    # Crowns (D27xx)
    # ------------------------------------------------------------------
    {
        "code": "D2740",
        "name": "Crown - porcelain/ceramic",
        "category": "Crown",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW", "PA (post-prep)"],
            "note": "Most carriers require a pre-op PA showing decay, fracture, or prior restoration failure.",
        },
    },
    {
        "code": "D2750",
        "name": "Crown - porcelain fused to high noble metal",
        "category": "Crown",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW", "PA (post-prep)"],
            "note": "Include narrative describing structural loss and reason PFM was chosen.",
        },
    },
    {
        "code": "D2751",
        "name": "Crown - porcelain fused to predominantly base metal",
        "category": "Crown",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW", "PA (post-prep)"],
            "note": "Base-metal PFM alternative — often used by carriers as the alternate-benefit ceiling.",
        },
    },
    {
        "code": "D2752",
        "name": "Crown - porcelain fused to noble metal",
        "category": "Crown",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["BW", "PA (post-prep)"],
            "note": "",
        },
    },

    # ------------------------------------------------------------------
    # Endodontics (D3xxx)
    # ------------------------------------------------------------------
    {
        "code": "D3310",
        "name": "Endodontic therapy, anterior tooth (excluding final restoration)",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)", "PA (post-op with obturation)"],
            "recommended": ["Working length film"],
            "note": "Document pulpal diagnosis (necrosis, irreversible pulpitis) and any periapical pathology.",
        },
    },
    {
        "code": "D3320",
        "name": "Endodontic therapy, premolar tooth (excluding final restoration)",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)", "PA (post-op with obturation)"],
            "recommended": ["Working length film"],
            "note": "Document pulpal diagnosis and any periapical pathology. Two-canal premolars often need extra justification.",
        },
    },
    {
        "code": "D3330",
        "name": "Endodontic therapy, molar tooth (excluding final restoration)",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)", "PA (post-op showing obturation of all canals)"],
            "recommended": ["Working length film", "PA of separate mesial/distal roots if unusual anatomy"],
            "note": "Document pulpal necrosis or irreversible pulpitis; note number of canals treated (3-4 for molars).",
        },
    },
    {
        "code": "D3346",
        "name": "Retreatment of previous root canal therapy - anterior",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing prior obturation and reason for failure"],
            "recommended": ["PA (post-retreatment)"],
            "note": "Document reason for retreatment (persistent periapical lesion, inadequate obturation, new symptoms). Date of original endodontic therapy required.",
        },
    },
    {
        "code": "D3347",
        "name": "Retreatment of previous root canal therapy - premolar",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing prior obturation and reason for failure"],
            "recommended": ["PA (post-retreatment)"],
            "note": "Document reason for retreatment and original endo date.",
        },
    },
    {
        "code": "D3348",
        "name": "Retreatment of previous root canal therapy - molar",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing prior obturation and reason for failure"],
            "recommended": ["PA (post-retreatment)", "CBCT if complex anatomy"],
            "note": "Molar retreatments often have highest denial rates. Document all canals located, missed anatomy from prior treatment, and reason for failure.",
        },
    },
    {
        "code": "D3410",
        "name": "Apicoectomy - anterior",
        "category": "Endodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing persistent periapical lesion"],
            "recommended": ["CBCT"],
            "note": "Surgical endo. Document why non-surgical retreatment is not indicated or has failed.",
        },
    },

    # ------------------------------------------------------------------
    # Periodontics (D4xxx)
    # ------------------------------------------------------------------
    {
        "code": "D4210",
        "name": "Gingivectomy or gingivoplasty - four or more contiguous teeth per quadrant",
        "category": "Periodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PA of area"],
            "recommended": ["PHOTO showing tissue overgrowth or pocketing"],
            "note": "Document quadrant, number of teeth involved (4+), and pocket depths or tissue overgrowth.",
        },
    },
    {
        "code": "D4249",
        "name": "Clinical crown lengthening - hard tissue",
        "category": "Periodontics",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA (pre-op)"],
            "recommended": ["PHOTO"],
            "note": "Document biologic width violation, subgingival caries, or short clinical crown height. Bone removal, not just tissue.",
        },
    },
    {
        "code": "D4260",
        "name": "Osseous surgery (including flap and closure) - four or more teeth per quadrant",
        "category": "Periodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PA of quadrant"],
            "recommended": ["Perio charting attached"],
            "note": "Document 5+ mm pockets, bone loss, and failure of prior non-surgical therapy (SRP).",
        },
    },
    {
        "code": "D4341",
        "name": "Periodontal scaling and root planing (SRP) - four or more teeth per quadrant",
        "category": "Periodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PA of quadrant"],
            "recommended": ["Perio charting attached (probing depths)"],
            "note": "Requires probing depths >=4mm on 4+ teeth in the quadrant with bleeding on probing. Attach perio chart.",
        },
    },
    {
        "code": "D4342",
        "name": "Periodontal scaling and root planing (SRP) - one to three teeth per quadrant",
        "category": "Periodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["PA of area"],
            "recommended": ["Perio charting attached"],
            "note": "For 1-3 teeth per quadrant with 4+ mm pockets and BOP. Attach perio chart.",
        },
    },
    {
        "code": "D4910",
        "name": "Periodontal maintenance",
        "category": "Periodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["Perio charting attached"],
            "note": "Following completion of active periodontal therapy. Not the same as prophy (D1110). Typical frequency: 4 per year (every 3 months).",
        },
    },

    # ------------------------------------------------------------------
    # Extractions & Oral Surgery (D7xxx)
    # ------------------------------------------------------------------
    {
        "code": "D7140",
        "name": "Extraction, erupted tooth or exposed root (elevation and/or forceps)",
        "category": "Extraction",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of tooth"],
            "recommended": [],
            "note": "Include reason (caries, fracture, perio, mobility, orthodontic, non-restorable).",
        },
    },
    {
        "code": "D7210",
        "name": "Extraction, erupted tooth requiring removal of bone and/or sectioning",
        "category": "Extraction",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of tooth"],
            "recommended": ["PANO if adjacent structures"],
            "note": "Surgical extraction. Document bone removal, sectioning, or elevation of a mucoperiosteal flap.",
        },
    },
    {
        "code": "D7220",
        "name": "Removal of impacted tooth - soft tissue",
        "category": "Extraction",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PANO or PA showing impaction"],
            "recommended": ["CBCT if proximity to nerve"],
            "note": "Tooth covered by soft tissue only. Common with third molars.",
        },
    },
    {
        "code": "D7230",
        "name": "Removal of impacted tooth - partially bony",
        "category": "Extraction",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PANO or PA showing impaction"],
            "recommended": ["CBCT"],
            "note": "Part of crown covered by bone. Document bony coverage and any pathology.",
        },
    },
    {
        "code": "D7240",
        "name": "Removal of impacted tooth - completely bony",
        "category": "Extraction",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PANO or PA showing full bony impaction"],
            "recommended": ["CBCT"],
            "note": "Fully bone-encased. Document proximity to inferior alveolar nerve or maxillary sinus if relevant.",
        },
    },
    {
        "code": "D7250",
        "name": "Surgical removal of residual tooth roots (cutting procedure)",
        "category": "Extraction",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing retained roots"],
            "recommended": [],
            "note": "Document that roots were retained from prior extraction or fractured during extraction.",
        },
    },
    {
        "code": "D7952",
        "name": "Sinus augmentation via a vertical approach",
        "category": "Bone Graft",
        "requires_tooth": False,
        "radiographs": {
            "required": ["PA or CBCT showing sinus floor and residual bone height"],
            "recommended": ["CBCT"],
            "note": "Crestal (osteotome) sinus lift. Document residual bone height and planned implant site.",
        },
    },
    {
        "code": "D7953",
        "name": "Bone replacement graft for ridge preservation - per site",
        "category": "Bone Graft",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of extraction site"],
            "recommended": ["PHOTO of socket at time of graft"],
            "note": "Same-day-as-extraction. Document graft material used and planned future restoration (implant, bridge, etc.).",
        },
    },

    # ------------------------------------------------------------------
    # Implant + Fixed Prosthodontics (D6xxx)
    # ------------------------------------------------------------------
    {
        "code": "D6010",
        "name": "Surgical placement of implant body: endosteal implant",
        "category": "Implant",
        "requires_tooth": True,
        "radiographs": {
            "required": ["CBCT or PANO (pre-op)", "PA (immediate post-op)"],
            "recommended": [],
            "note": "Include site (tooth number), reason for prior tooth loss, and treatment plan (single crown, bridge abutment, overdenture).",
        },
    },
    {
        "code": "D6057",
        "name": "Custom fabricated abutment - includes modification and placement",
        "category": "Implant",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA showing implant osseointegration"],
            "recommended": [],
            "note": "Custom abutment for angulation or emergence profile requirements.",
        },
    },
    {
        "code": "D6058",
        "name": "Abutment supported porcelain/ceramic crown",
        "category": "Implant",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of seated abutment"],
            "recommended": [],
            "note": "Final implant crown. Document date of implant placement and abutment used.",
        },
    },
    {
        "code": "D6210",
        "name": "Pontic - cast high noble metal",
        "category": "Bridge",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of edentulous site + abutment teeth"],
            "recommended": [],
            "note": "Bridge pontic. Bill with retainer codes (D6750/D6751/D6752). Document edentulous span and reason implant was not chosen.",
        },
    },
    {
        "code": "D6240",
        "name": "Pontic - porcelain fused to high noble metal",
        "category": "Bridge",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of edentulous site + abutment teeth"],
            "recommended": [],
            "note": "Bill with retainer codes. Document edentulous span, date of tooth loss, why implant was not chosen (medical, financial, anatomical).",
        },
    },
    {
        "code": "D6750",
        "name": "Retainer crown - porcelain fused to high noble metal",
        "category": "Bridge",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of abutment tooth"],
            "recommended": ["BW"],
            "note": "Abutment/retainer side of a fixed bridge. Bill separately for each retainer crown.",
        },
    },
    {
        "code": "D6751",
        "name": "Retainer crown - porcelain fused to predominantly base metal",
        "category": "Bridge",
        "requires_tooth": True,
        "radiographs": {
            "required": ["PA of abutment tooth"],
            "recommended": ["BW"],
            "note": "Base-metal alternative — often the carrier's alternate-benefit ceiling.",
        },
    },

    # ------------------------------------------------------------------
    # Removable Prosthodontics (D5xxx) - complete + partial dentures
    # ------------------------------------------------------------------
    {
        "code": "D5110",
        "name": "Complete denture - maxillary",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["PANO showing edentulous ridge and any residual roots"],
            "note": "Fully edentulous upper arch. Document date of last extractions and any residual anatomy affecting fit.",
        },
    },
    {
        "code": "D5120",
        "name": "Complete denture - mandibular",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["PANO showing edentulous ridge"],
            "note": "Fully edentulous lower arch. Document ridge form, tori, and prior denture history if applicable.",
        },
    },
    {
        "code": "D5130",
        "name": "Immediate denture - maxillary",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PANO"],
            "recommended": [],
            "note": "Delivered same day as remaining teeth are extracted. Document extraction plan and prosthetic timeline (temporary vs definitive).",
        },
    },
    {
        "code": "D5140",
        "name": "Immediate denture - mandibular",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PANO"],
            "recommended": [],
            "note": "Delivered same day as remaining teeth are extracted.",
        },
    },
    {
        "code": "D5211",
        "name": "Maxillary partial denture - resin base (including retentive/clasping materials, rests, and teeth)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PANO showing edentulous spaces and abutment teeth"],
            "recommended": [],
            "note": "Resin (flipper) partial. Document teeth being replaced (tooth numbers) and abutment/rest teeth.",
        },
    },
    {
        "code": "D5212",
        "name": "Mandibular partial denture - resin base",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PANO"],
            "recommended": [],
            "note": "Document teeth being replaced and abutment/rest teeth.",
        },
    },
    {
        "code": "D5213",
        "name": "Maxillary partial denture - cast metal framework with resin denture bases",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PANO", "PA of abutment teeth"],
            "recommended": ["PHOTO of edentulous spaces"],
            "note": "Cast framework (chrome-cobalt) partial. Document teeth replaced, abutments used for rests/clasps, and periodontal health of abutments.",
        },
    },
    {
        "code": "D5214",
        "name": "Mandibular partial denture - cast metal framework with resin denture bases",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PANO", "PA of abutment teeth"],
            "recommended": ["PHOTO of edentulous spaces"],
            "note": "Document teeth replaced, abutment health, and Kennedy classification if relevant.",
        },
    },
    {
        "code": "D5225",
        "name": "Maxillary partial denture - flexible base (including any clasps, rests, and teeth)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PANO"],
            "recommended": ["PHOTO"],
            "note": "Flexible thermoplastic (e.g., Valplast). Document metal allergy or esthetic requirement if requesting over cast-metal partial.",
        },
    },
    {
        "code": "D5226",
        "name": "Mandibular partial denture - flexible base",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": ["FMX or PANO"],
            "recommended": ["PHOTO"],
            "note": "Flexible thermoplastic partial. Document rationale (allergy, esthetics, undercuts).",
        },
    },

    # ------------------------------------------------------------------
    # Removable Prosthodontics - adjustments, repairs, relines (D54xx-D57xx)
    # ------------------------------------------------------------------
    {
        "code": "D5410",
        "name": "Adjust complete denture - maxillary",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Post-delivery adjustment beyond the initial adjustment period. Note the specific sore spots or occlusal issues addressed.",
        },
    },
    {
        "code": "D5411",
        "name": "Adjust complete denture - mandibular",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Post-delivery adjustment.",
        },
    },
    {
        "code": "D5421",
        "name": "Adjust partial denture - maxillary",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Post-delivery adjustment to clasps, rests, or occlusion.",
        },
    },
    {
        "code": "D5422",
        "name": "Adjust partial denture - mandibular",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Post-delivery adjustment.",
        },
    },
    {
        "code": "D5510",
        "name": "Repair broken complete denture base, mandibular or maxillary",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["PHOTO of fracture"],
            "note": "Document location and extent of fracture, and how the denture broke if known.",
        },
    },
    {
        "code": "D5730",
        "name": "Reline complete maxillary denture (chairside)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "In-office reline. Document ridge resorption or fit loss since delivery.",
        },
    },
    {
        "code": "D5731",
        "name": "Reline complete mandibular denture (chairside)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "In-office reline.",
        },
    },
    {
        "code": "D5740",
        "name": "Reline maxillary partial denture (chairside)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "In-office reline of partial. Note abutment status.",
        },
    },
    {
        "code": "D5741",
        "name": "Reline mandibular partial denture (chairside)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "In-office reline of partial.",
        },
    },
    {
        "code": "D5750",
        "name": "Reline complete maxillary denture (laboratory)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Lab reline. Document ridge resorption since delivery and reason chairside reline is not appropriate.",
        },
    },
    {
        "code": "D5751",
        "name": "Reline complete mandibular denture (laboratory)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Lab reline.",
        },
    },
    {
        "code": "D5760",
        "name": "Reline maxillary partial denture (laboratory)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Lab reline of partial.",
        },
    },
    {
        "code": "D5761",
        "name": "Reline mandibular partial denture (laboratory)",
        "category": "Removable Prosthodontics",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Lab reline of partial.",
        },
    },

    # ------------------------------------------------------------------
    # Adjunctive general services (D9xxx) - visits, palliative care, consults
    # ------------------------------------------------------------------
    {
        "code": "D9110",
        "name": "Palliative treatment of dental pain - per visit",
        "category": "Adjunctive",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["PA of area of concern"],
            "note": "Emergency/urgent visit for pain relief when definitive treatment isn't performed same day (e.g., patient in acute pain, medication only, temporary sedative filling). Document chief complaint, findings, treatment provided, and follow-up plan.",
        },
    },
    {
        "code": "D9310",
        "name": "Consultation - diagnostic service by dentist or physician other than the requesting dentist",
        "category": "Adjunctive",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Second-opinion or specialist consult. Document referring provider, reason for consult, and written report generated. Not billable with a same-day evaluation code by same provider.",
        },
    },
    {
        "code": "D9440",
        "name": "Office visit - after regularly scheduled hours",
        "category": "Adjunctive",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "After-hours emergency visit. Document date, time seen (outside normal hours), and reason for the after-hours call.",
        },
    },
    {
        "code": "D9450",
        "name": "Case presentation - subsequent to detailed and extensive treatment planning",
        "category": "Adjunctive",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": [],
            "note": "Time spent presenting a comprehensive treatment plan to the patient. Document plan complexity, time spent, and materials reviewed with patient.",
        },
    },

    # ------------------------------------------------------------------
    # Occlusal guards (D99xx) and other adjunctive
    # ------------------------------------------------------------------
    {
        "code": "D9944",
        "name": "Occlusal guard - hard appliance, full arch",
        "category": "Occlusal Guard",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["PHOTO of wear facets/abfractions"],
            "note": "Document bruxism signs (wear facets, abfractions, muscle tenderness). Carrier may exclude if TMD-only.",
        },
    },
    {
        "code": "D9945",
        "name": "Occlusal guard - soft appliance, full arch",
        "category": "Occlusal Guard",
        "requires_tooth": False,
        "radiographs": {
            "required": [],
            "recommended": ["PHOTO of wear facets"],
            "note": "",
        },
    },
]


def get_procedure(code: str):
    for p in PROCEDURES:
        if p["code"] == code:
            return p
    return None
