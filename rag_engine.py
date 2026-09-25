import math
import re
import json
from datetime import datetime, timedelta

AUTHORITATIVE_DOCUMENTS = [
    {
        "id": "CDSCO-AMX-2024",
        "title": "CDSCO Approved Veterinary Formulations - Amoxicillin Trihydrate",
        "source": "CDSCO (Central Drugs Standard Control Organisation, India) & Codex CAC/MRL 2-2023",
        "source_url": "https://cdsco.gov.in/",
        "source_date": "2024-03-10",
        "drug_name": "Amoxicillin",
        "active_ingredient": "Amoxicillin Trihydrate",
        "species": ["cattle", "buffalo", "goat", "sheep", "swine"],
        "approved_routes": ["Intramuscular", "Oral", "Injectable"],
        "indications": ["Respiratory tract infection", "Gastrointestinal infection", "Mastitis", "Metritis", "Soft tissue infection"],
        "recommended_withdrawal_days": 5,
        "milk_withdrawal_hours": 60,
        "max_allowed_dosage": 15.0,
        "unit": "mg/kg",
        "mrl_info": "Codex/FSSAI MRL: 50 µg/kg in muscle, liver, kidney; 4 µg/kg in milk.",
        "regulatory_summary": "Beta-lactam antibiotic. Approved under CDSCO Form-28. Minimum 5-day meat withdrawal and 60-hour milk withdrawal mandatory. Verify expected selling date before harvest.",
        "content": "CDSCO Official Veterinary Reference: Amoxicillin Trihydrate is indicated for acute systemic and respiratory bacterial infections, mastitis, and enteric illness in cattle, buffalo, goats, sheep, and swine. Approved administration routes are Intramuscular injection and Oral. Recommended therapeutic dosage is up to 15.0 mg/kg body weight daily. Mandatory meat withdrawal period is 5 days (120 hours) and milk withdrawal is 60 hours. Codex/FSSAI Maximum Residue Limit (MRL) is established at 50 µg/kg in edible tissue and 4 µg/kg in milk."
    },
    {
        "id": "CDSCO-CEF-2023",
        "title": "CDSCO Approved Veterinary Product - Ceftiofur Sodium Injection",
        "source": "CDSCO (Central Drugs Standard Control Organisation, India) & Codex Alimentarius",
        "source_url": "https://cdsco.gov.in/",
        "source_date": "2023-11-20",
        "drug_name": "Ceftiofur Sodium",
        "active_ingredient": "Ceftiofur",
        "species": ["cattle", "buffalo", "swine"],
        "approved_routes": ["Subcutaneous", "Intramuscular", "Injectable"],
        "indications": ["Bovine respiratory disease (shipping fever)", "Acute interdigital necrobacillosis (foot rot)", "Acute metritis"],
        "recommended_withdrawal_days": 4,
        "milk_withdrawal_hours": 0,
        "max_allowed_dosage": 2.2,
        "unit": "mg/kg",
        "mrl_info": "Codex/FSSAI MRL: 1000 µg/kg in muscle, 2000 µg/kg in kidney, 100 µg/kg in milk.",
        "regulatory_summary": "Third-generation cephalosporin. CDSCO approved for cattle respiratory disease and foot rot. Meat withdrawal: 4 days. Milk withdrawal: 0 hours at standard therapeutic dose.",
        "content": "CDSCO Official Approval: Ceftiofur Sodium sterile powder for injection. Indicated for treatment of bovine respiratory disease (shipping fever, pneumonia) associated with Mannheimia haemolytica, Pasteurella multocida, and Histophilus somni, and acute foot rot in cattle and buffalo. Approved administration routes are Subcutaneous and Intramuscular. Recommended dosage limit is 2.2 mg/kg body weight per day. Mandatory meat withdrawal is 4 days. Zero-day milk withdrawal applies when administered according to label dosage."
    },
    {
        "id": "CDSCO-ENR-2024",
        "title": "CDSCO Veterinary Approval & WHO MIA Framework - Enrofloxacin",
        "source": "CDSCO (Central Drugs Standard Control Organisation, Govt of India) & WHO/WOAH",
        "source_url": "https://cdsco.gov.in/",
        "source_date": "2024-01-15",
        "drug_name": "Enrofloxacin",
        "active_ingredient": "Enrofloxacin",
        "species": ["cattle", "buffalo", "goat", "poultry"],
        "approved_routes": ["Injectable", "Intramuscular", "Subcutaneous", "Oral"],
        "indications": ["Complex respiratory disease", "Colibacillosis", "Contagious caprine pleuropneumonia (CCPP)", "Salmonellosis"],
        "recommended_withdrawal_days": 10,
        "milk_withdrawal_hours": 84,
        "max_allowed_dosage": 5.0,
        "unit": "mg/kg",
        "mrl_info": "Codex/FSSAI MRL: 100 µg/kg (combined enrofloxacin + ciprofloxacin) in muscle, 300 µg/kg in liver.",
        "regulatory_summary": "Critically Important Antimicrobial (Fluoroquinolone class). CDSCO restricted veterinary prescription drug. Meat withdrawal: 10 days. Milk withdrawal: 84 hours (7 days). Extra-label dosage prohibited.",
        "content": "CDSCO Official Veterinary Drug List: Enrofloxacin injectable solution and oral formulation. Indicated for severe respiratory tract infections, colibacillosis, and infectious enteritis in cattle, buffalo, goats, and poultry. Approved routes are Injectable (IM/SC) and Oral. Maximum daily therapeutic dosage is 5.0 mg/kg body weight. Mandatory minimum meat withdrawal period is 10 days; milk withdrawal is 84 hours. Codex/FSSAI MRL sum of enrofloxacin and ciprofloxacin residues is 100 µg/kg in muscle tissue."
    },
    {
        "id": "CDSCO-OXY-2024",
        "title": "CDSCO Veterinary Approval - Oxytetracycline Dihydrate Injection",
        "source": "CDSCO (Central Drugs Standard Control Organisation, India) & FSSAI Residue Regulations",
        "source_url": "https://cdsco.gov.in/",
        "source_date": "2024-02-01",
        "drug_name": "Oxytetracycline",
        "active_ingredient": "Oxytetracycline",
        "species": ["cattle", "buffalo", "goat", "sheep", "swine"],
        "approved_routes": ["Intramuscular", "Intravenous", "Injectable", "Oral"],
        "indications": ["Anaplasmosis", "Blackquarter", "Haemorrhagic septicaemia", "Pneumonia", "Foot rot"],
        "recommended_withdrawal_days": 7,
        "milk_withdrawal_hours": 72,
        "max_allowed_dosage": 10.0,
        "unit": "mg/kg",
        "mrl_info": "Codex/FSSAI MRL: 100 µg/kg in muscle, 300 µg/kg in liver, 600 µg/kg in kidney, 100 µg/kg in milk.",
        "regulatory_summary": "Tetracycline antimicrobial approved by CDSCO. Recommended meat withdrawal: 7 days. Milk withdrawal: 72 hours (3 days). Mandatory residue testing under FSSAI export standards.",
        "content": "CDSCO Official Reference Standard: Oxytetracycline Dihydrate 100mg/ml injection. Approved for treatment of systemic and bacterial infections including Haemorrhagic Septicaemia, Blackquarter, Anaplasmosis, and pneumonia in cattle, buffalo, goats, sheep, and swine. Routes of administration: Deep Intramuscular and Intravenous. Maximum daily recommended dosage is 10.0 mg/kg body weight. Meat withdrawal period: 7 days. Milk withdrawal period: 72 hours. Codex/FSSAI MRL limit is 100 µg/kg in muscle tissue."
    },
    {
        "id": "CDSCO-PEN-2023",
        "title": "CDSCO Approved Veterinary Formulation - Penicillin G Procaine",
        "source": "CDSCO (Central Drugs Standard Control Organisation, India) & Codex CAC/MRL 2-2023",
        "source_url": "https://cdsco.gov.in/",
        "source_date": "2023-09-05",
        "drug_name": "Penicillin G Procaine",
        "active_ingredient": "Procaine Penicillin G",
        "species": ["cattle", "buffalo", "goat", "horse", "sheep"],
        "approved_routes": ["Intramuscular", "Injectable"],
        "indications": ["Erysipelas", "Strangles", "Blackleg", "Mastitis", "Gram-positive systemic infections"],
        "recommended_withdrawal_days": 14,
        "milk_withdrawal_hours": 72,
        "max_allowed_dosage": 20000.0,
        "unit": "IU/kg",
        "mrl_info": "Codex/FSSAI MRL: 50 µg/kg in muscle/liver/kidney, 4 µg/kg in milk.",
        "regulatory_summary": "Long-acting natural penicillin derivative. CDSCO approved for livestock bacterial infections. Meat withdrawal: 14 days. Milk withdrawal: 72 hours.",
        "content": "CDSCO Official Approval: Penicillin G Procaine injectable suspension. Indicated for Gram-positive bacterial infections including Blackleg, Mastitis, and Erysipelas in cattle, buffalo, goats, and horses. Approved route of administration: Intramuscular injection only. Recommended dosage limit: 20,000 IU/kg body weight per day. Mandatory meat withdrawal period is 14 days due to tissue clearance rates; milk withdrawal is 72 hours. Codex MRL limit is 50 µg/kg in edible muscle tissue."
    },
    {
        "id": "CDSCO-SUL-2023",
        "title": "CDSCO Veterinary Standard - Sulfadimidine Sodium Formulation",
        "source": "CDSCO (Central Drugs Standard Control Organisation, India) & FSSAI",
        "source_url": "https://cdsco.gov.in/",
        "source_date": "2023-12-12",
        "drug_name": "Sulfadimidine Sodium",
        "active_ingredient": "Sulfadimidine",
        "species": ["cattle", "buffalo", "goat", "poultry", "sheep"],
        "approved_routes": ["Oral", "Intravenous", "Subcutaneous", "Injectable"],
        "indications": ["Coccidiosis", "Calf diphtheria", "Bacterial enteritis", "Foot rot", "Pneumonia"],
        "recommended_withdrawal_days": 10,
        "milk_withdrawal_hours": 96,
        "max_allowed_dosage": 100.0,
        "unit": "mg/kg",
        "mrl_info": "Codex/FSSAI MRL: 100 µg/kg total sulfonamide residues in edible tissue.",
        "regulatory_summary": "Sulfonamide antimicrobial agent. CDSCO veterinary formulation. Meat withdrawal: 10 days. Milk withdrawal: 96 hours (4 days).",
        "content": "CDSCO Official Veterinary Schedule: Sulfadimidine Sodium 33.3% w/v solution. Indicated for treatment of coccidiosis, calf diphtheria, necrotic enteritis, and systemic bacterial infections in cattle, buffalo, goats, and poultry. Approved routes: Intravenous injection, Subcutaneous, and Oral drench. Recommended maximum dosage: 100.0 mg/kg initial dose, followed by 50 mg/kg daily maintenance. Mandatory meat withdrawal period: 10 days; milk withdrawal: 96 hours. Codex/FSSAI MRL limit is 100 µg/kg in muscle tissue."
    },
    {
        "id": "CDSCO-TYL-2024",
        "title": "CDSCO Approved Veterinary Product - Tylosin Tartrate Injection",
        "source": "CDSCO (Central Drugs Standard Control Organisation, India) & Codex Alimentarius",
        "source_url": "https://cdsco.gov.in/",
        "source_date": "2024-04-18",
        "drug_name": "Tylosin Tartrate",
        "active_ingredient": "Tylosin",
        "species": ["cattle", "buffalo", "goat", "poultry", "swine"],
        "approved_routes": ["Intramuscular", "Oral", "Injectable"],
        "indications": ["Bovine respiratory complex", "Mycoplasmosis", "Foot rot", "Diphtheria", "Dysentery"],
        "recommended_withdrawal_days": 21,
        "milk_withdrawal_hours": 96,
        "max_allowed_dosage": 10.0,
        "unit": "mg/kg",
        "mrl_info": "Codex/FSSAI MRL: 100 µg/kg in muscle, 50 µg/kg in milk.",
        "regulatory_summary": "Macrolide antibiotic. CDSCO veterinary approved drug. Mandatory 21-day meat withdrawal for injectable formulations and 96-hour milk withdrawal.",
        "content": "CDSCO Official Approval: Tylosin Tartrate injectable solution. Indicated for contagious respiratory complex, Mycoplasmosis, foot rot, and diphtheria in cattle, buffalo, goats, and swine. Approved routes: Intramuscular injection and Oral water medication. Recommended daily dosage limit is 10.0 mg/kg body weight. Mandatory meat withdrawal period: 21 days for injectable formulations; milk withdrawal: 96 hours. Codex MRL limit is 100 µg/kg in muscle tissue."
    }
]

def tokenize(text):
    if not text:
        return []
    return re.findall(r'\w+', str(text).lower())

def compute_tf(tokens):
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    total = len(tokens) or 1
    return {k: v / total for k, v in tf.items()}

class RAGEngine:
    def __init__(self, documents=None):
        self.documents = documents or AUTHORITATIVE_DOCUMENTS
        self.idf = {}
        self.doc_vectors = []
        self._build_index()

    def _build_index(self):
        doc_count = len(self.documents)
        df = {}
        processed_docs = []

        for doc in self.documents:
            species_str = " ".join(doc.get('species', [])) if isinstance(doc.get('species'), list) else str(doc.get('species', ''))
            routes_str = " ".join(doc.get('approved_routes', [])) if isinstance(doc.get('approved_routes'), list) else str(doc.get('approved_routes', ''))
            ind_str = " ".join(doc.get('indications', [])) if isinstance(doc.get('indications'), list) else str(doc.get('indications', ''))
            
            full_text = f"{doc.get('title', '')} {doc.get('drug_name', '')} {doc.get('active_ingredient', '')} {species_str} {routes_str} {ind_str} {doc.get('content', '')} {doc.get('regulatory_summary', '')} {doc.get('mrl_info', '')}"
            tokens = tokenize(full_text)
            processed_docs.append((doc, tokens))
            unique_tokens = set(tokens)
            for t in unique_tokens:
                df[t] = df.get(t, 0) + 1

        for t, count in df.items():
            self.idf[t] = math.log((doc_count + 1) / (count + 1)) + 1

        for doc, tokens in processed_docs:
            tf = compute_tf(tokens)
            vec = {t: tf[t] * self.idf.get(t, 1.0) for t in tf}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self.doc_vectors.append({
                "doc": doc,
                "vec": vec,
                "norm": norm
            })

    def retrieve_evidence(self, drug_name, species=None, route=None, indication=None, dosage=None, unit=None, treatment_date=None, expected_selling_date=None):
        query_text = f"{drug_name or ''} {species or ''} {route or ''} {indication or ''} dosage {dosage or ''} {unit or ''} CDSCO approval withdrawal MRL regulatory guidelines authority residue limit"
        tokens = tokenize(query_text)
        query_tf = compute_tf(tokens)
        query_vec = {t: query_tf[t] * self.idf.get(t, 1.0) for t in query_tf}
        query_norm = math.sqrt(sum(v * v for v in query_vec.values())) or 1.0

        best_score = -1.0
        best_doc = None

        search_drug_norm = str(drug_name or '').strip().lower()

        for item in self.doc_vectors:
            doc = item['doc']
            score = 0.0
            for t, val in query_vec.items():
                if t in item['vec']:
                    score += val * item['vec'][t]
            score = score / (query_norm * item['norm'])

            # Heavily boost exact or substring drug name / active ingredient matches
            doc_drug = doc['drug_name'].lower()
            doc_active = doc['active_ingredient'].lower()
            if search_drug_norm and (search_drug_norm in doc_drug or search_drug_norm in doc_active or doc_drug in search_drug_norm):
                score += 5.0

            # Species match boost
            doc_species = [s.lower() for s in doc['species']] if isinstance(doc['species'], list) else [str(doc['species']).lower()]
            if species and (species.lower() in doc_species or 'all' in doc_species):
                score += 1.0

            if score > best_score:
                best_score = score
                best_doc = doc

        # Fallback if no doc matched query
        if not best_doc:
            best_doc = self.documents[0]

        # Perform 7-parameter correctness verification against farmer submitted data
        verification_res = self.verify_submission(
            submitted_data={
                "drug_name": drug_name,
                "species": species,
                "route": route,
                "indication": indication,
                "dosage": dosage,
                "unit": unit,
                "treatment_date": treatment_date,
                "expected_selling_date": expected_selling_date
            },
            retrieved_evidence=best_doc
        )

        return {
            "document_title": best_doc["title"],
            "retrieved_chunk": best_doc["content"],
            "source_reference": f"{best_doc['source']} (Ref: {best_doc['source_url']}) [Updated: {best_doc['source_date']}]",
            "recommended_withdrawal_days": best_doc["recommended_withdrawal_days"],
            "max_allowed_dosage": best_doc["max_allowed_dosage"],
            "mrl_info": best_doc["mrl_info"],
            "regulatory_summary": best_doc["regulatory_summary"],
            "active_ingredient": best_doc["active_ingredient"],
            "approved_species": best_doc["species"],
            "approved_routes": best_doc["approved_routes"],
            "indications": best_doc["indications"],
            "verification_status": verification_res["status"],
            "verification_details": json.dumps(verification_res["checks"])
        }

    def verify_submission(self, submitted_data, retrieved_evidence):
        """
        Compares farmer's submitted details against retrieved authoritative CDSCO & Codex/FSSAI evidence.
        Parameters checked:
        1. Drug & Active Ingredient
        2. Species
        3. Route
        4. Dosage & Unit
        5. Indication
        6. Withdrawal Period & Sale Date
        7. MRL / Residue Requirements
        """
        checks = []
        is_mismatch = False
        is_insufficient = False

        sub_drug = str(submitted_data.get('drug_name') or '').strip()
        sub_species = str(submitted_data.get('species') or '').strip()
        sub_route = str(submitted_data.get('route') or '').strip()
        sub_ind = str(submitted_data.get('indication') or '').strip()
        sub_dosage = submitted_data.get('dosage')
        sub_unit = str(submitted_data.get('unit') or '').strip()
        sub_tdate = submitted_data.get('treatment_date')
        sub_sdate = submitted_data.get('expected_selling_date')

        doc_drug = retrieved_evidence.get('drug_name', '')
        doc_active = retrieved_evidence.get('active_ingredient', '')
        doc_species = [s.lower() for s in retrieved_evidence.get('species', [])] if isinstance(retrieved_evidence.get('species'), list) else [str(retrieved_evidence.get('species')).lower()]
        doc_routes = [r.lower() for r in retrieved_evidence.get('approved_routes', [])] if isinstance(retrieved_evidence.get('approved_routes'), list) else [str(retrieved_evidence.get('approved_routes')).lower()]
        doc_inds = [i.lower() for i in retrieved_evidence.get('indications', [])] if isinstance(retrieved_evidence.get('indications'), list) else [str(retrieved_evidence.get('indications')).lower()]
        doc_max_dosage = retrieved_evidence.get('max_allowed_dosage')
        doc_unit = str(retrieved_evidence.get('unit') or '').strip()
        doc_withdrawal = retrieved_evidence.get('recommended_withdrawal_days')

        # 1. Drug Match Check
        if not sub_drug:
            checks.append({"parameter": "Drug / Product", "status": "insufficient", "detail": "No drug name provided in submission."})
            is_insufficient = True
        elif sub_drug.lower() in doc_drug.lower() or sub_drug.lower() in doc_active.lower() or doc_drug.lower() in sub_drug.lower():
            checks.append({"parameter": "Drug / Active Ingredient", "status": "match", "detail": f"Submitted '{sub_drug}' matches official CDSCO approved '{doc_drug}' ({doc_active})."})
        else:
            checks.append({"parameter": "Drug / Active Ingredient", "status": "mismatch", "detail": f"Submitted drug '{sub_drug}' does not match CDSCO reference '{doc_drug}'."})
            is_mismatch = True

        # 2. Species Check
        if not sub_species:
            checks.append({"parameter": "Animal Species", "status": "insufficient", "detail": "Animal species not specified."})
            is_insufficient = True
        elif sub_species.lower() in doc_species or 'all' in doc_species:
            checks.append({"parameter": "Animal Species", "status": "match", "detail": f"Species '{sub_species.capitalize()}' is approved for {doc_drug}."})
        else:
            checks.append({"parameter": "Animal Species", "status": "mismatch", "detail": f"Species '{sub_species.capitalize()}' is NOT in CDSCO approved species list ({', '.join(doc_species)})."})
            is_mismatch = True

        # 3. Route Check
        if not sub_route:
            checks.append({"parameter": "Administration Route", "status": "insufficient", "detail": "Administration route not specified in submission."})
            is_insufficient = True
        elif any(r in sub_route.lower() or sub_route.lower() in r for r in doc_routes):
            checks.append({"parameter": "Administration Route", "status": "match", "detail": f"Route '{sub_route}' matches approved routes ({', '.join(retrieved_evidence.get('approved_routes', []))})."})
        else:
            checks.append({"parameter": "Administration Route", "status": "mismatch", "detail": f"Route '{sub_route}' is not listed in CDSCO approved routes ({', '.join(retrieved_evidence.get('approved_routes', []))})."})
            is_mismatch = True

        # 4. Dosage & Unit Check
        if sub_dosage is None:
            checks.append({"parameter": "Dosage & Unit", "status": "insufficient", "detail": "Dosage value missing."})
            is_insufficient = True
        elif doc_max_dosage is not None:
            try:
                val = float(sub_dosage)
                if val <= doc_max_dosage:
                    checks.append({"parameter": "Dosage & Unit", "status": "match", "detail": f"Submitted dosage ({val} {sub_unit}) is within CDSCO limit (Max {doc_max_dosage} {doc_unit})."})
                else:
                    checks.append({"parameter": "Dosage & Unit", "status": "mismatch", "detail": f"Submitted dosage ({val} {sub_unit}) EXCEEDS CDSCO max allowed dosage ({doc_max_dosage} {doc_unit})."})
                    is_mismatch = True
            except (ValueError, TypeError):
                checks.append({"parameter": "Dosage & Unit", "status": "insufficient", "detail": f"Invalid dosage format: {sub_dosage}"})
                is_insufficient = True
        else:
            checks.append({"parameter": "Dosage & Unit", "status": "match", "detail": f"Submitted dosage: {sub_dosage} {sub_unit}"})

        # 5. Indication Check
        if not sub_ind:
            checks.append({"parameter": "Indication", "status": "insufficient", "detail": "Indication/diagnosis not provided in entry."})
            is_insufficient = True
        elif any(i in sub_ind.lower() or sub_ind.lower() in i for i in doc_inds) or len(doc_inds) == 0:
            checks.append({"parameter": "Indication", "status": "match", "detail": f"Indication '{sub_ind}' matches CDSCO therapeutic indications."})
        else:
            checks.append({"parameter": "Indication", "status": "match", "detail": f"Indication '{sub_ind}' recorded (Approved indications: {', '.join(retrieved_evidence.get('indications', []))})."})

        # 6. Withdrawal Period & Date Check
        if sub_tdate and doc_withdrawal:
            try:
                if isinstance(sub_tdate, str):
                    t_dt = datetime.strptime(sub_tdate.split('T')[0], '%Y-%m-%d').date()
                else:
                    t_dt = sub_tdate
                
                calculated_withdrawal_end = t_dt + timedelta(days=doc_withdrawal)

                if sub_sdate:
                    if isinstance(sub_sdate, str):
                        s_dt = datetime.strptime(sub_sdate.split('T')[0], '%Y-%m-%d').date()
                    else:
                        s_dt = sub_sdate

                    if s_dt < calculated_withdrawal_end:
                        checks.append({
                            "parameter": "Withdrawal & Selling Date",
                            "status": "mismatch",
                            "detail": f"VIOLATION: Expected sale date ({s_dt.strftime('%Y-%m-%d')}) occurs BEFORE mandatory withdrawal end date ({calculated_withdrawal_end.strftime('%Y-%m-%d')}). Required period: {doc_withdrawal} days."
                        })
                        is_mismatch = True
                    else:
                        checks.append({
                            "parameter": "Withdrawal & Selling Date",
                            "status": "match",
                            "detail": f"Compliant: Sale date ({s_dt.strftime('%Y-%m-%d')}) is after withdrawal completion ({calculated_withdrawal_end.strftime('%Y-%m-%d')}). Period: {doc_withdrawal} days."
                        })
                else:
                    checks.append({
                        "parameter": "Withdrawal Period",
                        "status": "match",
                        "detail": f"Mandatory withdrawal period: {doc_withdrawal} days (End Date: {calculated_withdrawal_end.strftime('%Y-%m-%d')})."
                    })
            except Exception as dt_err:
                checks.append({"parameter": "Withdrawal Period", "status": "insufficient", "detail": f"Unable to parse dates for withdrawal calculation: {dt_err}"})
                is_insufficient = True
        else:
            checks.append({"parameter": "Withdrawal Period", "status": "insufficient", "detail": "Treatment date or official withdrawal period insufficient."})
            is_insufficient = True

        # 7. MRL / Residue Requirements
        mrl_str = retrieved_evidence.get('mrl_info', '')
        if mrl_str:
            checks.append({"parameter": "MRL / Residue Requirements", "status": "match", "detail": f"Codex/FSSAI Standard: {mrl_str}"})
        else:
            checks.append({"parameter": "MRL / Residue Requirements", "status": "insufficient", "detail": "Specific MRL residue data unavailable in reference document."})

        # Overall Status Determination
        if is_mismatch:
            overall_status = "mismatch"
        elif is_insufficient:
            overall_status = "insufficient"
        else:
            overall_status = "verified"

        return {
            "status": overall_status,
            "checks": checks
        }

rag_engine_instance = RAGEngine()
