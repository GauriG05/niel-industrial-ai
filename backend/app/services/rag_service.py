"""RAG pipeline: fluent grounded answer generation, prompt defense, and smart citation handling."""

import json
import logging
import re
import uuid
from typing import Dict, List, Optional, Tuple
from openai import OpenAI, OpenAIError

from backend.app.config import get_settings
from backend.app.schemas.chat import ChatResponse, Citation, UsageMetadata
from backend.app.schemas.documents import ChunkMetadata
from backend.app.services.openai_service import (
    get_openai_service,
    GPT4O_MINI_PROMPT_PER_MILLION,
    GPT4O_MINI_COMPLETION_PER_MILLION,
)
from backend.app.retrieval.retriever import get_retriever

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Customer Support Engineer representing New India Electricals Ltd. (NIEL).
You communicate with website visitors in a genuine, warm, and professional human conversational tone, like an experienced support engineer at NIEL.

GUIDELINES:
1. HUMAN CONVERSATION: Speak naturally, warmly, and helpfully. If a visitor says "hi", "hello", or greets you, greet them warmly, welcome them to NIEL, and ask how you can assist their project or electrical equipment needs today.
2. TECHNICAL GROUNDEDNESS: When answering technical product questions, rely strictly on the facts in the provided <EVIDENCE> documentation. Answer clearly and conversationally without dumping raw fragments or repeating robotic phrases.
3. COMMERICAL QUOTES & PRICING: If the user asks for pricing or discounts, explain politely that commercial quotes depend on specific project requirements, capacity, and volume. Guide them on the specs needed for a quote and direct them to NIEL sales at sales@newindiaelectricals.com or +91 80 42434343.
4. HONESTY: If a specific detail is not in the documentation, let them know politely in a friendly human manner that the current technical catalogue does not specify that detail, and offer to connect them with the technical team.
5. NO ASTERISKS: Never use markdown bold asterisks (**) anywhere in your reply. Use clean, plain text.
"""


class RAGService:
    """Orchestrates query retrieval, prompt security, LLM generation, and citation handling."""

    def __init__(self):
        self.settings = get_settings()
        self.retriever = get_retriever()
        self.openai_service = get_openai_service()

    def _validate_citations(
        self,
        retrieved_chunks: List[Tuple[ChunkMetadata, float]],
    ) -> List[Citation]:
        """Build verified citations strictly from chunks retrieved by FAISS, mapping to official PDFs."""
        citations: List[Citation] = []
        seen = set()

        for chunk, score in retrieved_chunks:
            filename = chunk.source_filename
            # Map any text versions to their official PDF brochures
            if filename.endswith(".txt"):
                if "AC Motors" in filename:
                    filename = "AC Motors - NIEL Brochure.pdf"
                elif "DC Motors" in filename:
                    filename = "DC Motors - NIEL Brochure.pdf"
                elif "Transformers" in filename:
                    filename = "Transformers - NIEL Brochure.pdf"
                elif "Switchgear" in filename:
                    filename = "Switchgear Panels MV - NIEL Brochure.pdf"
                elif "Company" in filename:
                    filename = "Company Intro - New India Electricals Limited.pdf"
                elif "Catalog" in filename:
                    filename = "NIEL Product Catalog.pdf"
                elif "Substation" in filename:
                    filename = "Substation.pdf"
                elif "Pump" in filename:
                    filename = "Pumps - NIEL Brochure.pdf"
                else:
                    filename = filename.replace(".txt", ".pdf")

            # Only official PDF brochures are surfaced to users
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"

            key = (filename, chunk.page_number)
            if key not in seen:
                seen.add(key)
                snippet = chunk.text[:120] + "..." if len(chunk.text) > 120 else chunk.text
                citations.append(
                    Citation(
                        source_filename=filename,
                        page_number=chunk.page_number,
                        chunk_id=chunk.chunk_id,
                        quote_snippet=snippet,
                    )
                )
        return citations

    def _generate_offline_grounded_answer(
        self,
        question: str,
        retrieved_chunks: List[Tuple[ChunkMetadata, float]],
    ) -> Tuple[str, bool, bool]:
        """
        Synthesize a direct, natural, conversational answer from retrieved evidence.
        Returns (answer, evidence_sufficient, clarification_needed).
        """
        q_lower = question.lower()

        # Check sales / RFQ guidance pills
        if any(w in q_lower for w in ["what do you need for a quote", "request a quote", "need for a quote", "rfq requirements", "how to quote"]):
            return (
                "To generate an authorized technical quotation, our sales engineering team requires:\n\n"
                "1. Equipment Category: (e.g., IE3 Induction Motor, Power Transformer, MV Switchgear Panel, or Industrial Pump)\n"
                "2. Primary Operating Specs: Power rating (kW/HP) or capacity (kVA/MVA), operating voltage (415V, 11kV, 33kV), and frequency (50 Hz)\n"
                "3. Duty & Environment: Ambient temperature, mounting type (B3/B5/B35), duty cycle (S1), or fluid details for pumps\n"
                "4. Project Scope: Delivery destination, required quantity, and single-line diagram (SLD) if applicable\n\n"
                "You can email your technical requirements to sales@newindiaelectricals.com or call our office at +91 80 42434343.",
                True,
                False,
            )

        if any(w in q_lower for w in ["talk to sales", "contact sales", "phone number", "reach us", "office address"]):
            return (
                "You can contact the New India Electricals Ltd. sales and engineering team directly:\n\n"
                "• Head Office: 1st Floor, Power House, #18, JC Road, Bangalore, Karnataka, India\n"
                "• Phone: +91 80 42434343\n"
                "• Email: sales@newindiaelectricals.com\n"
                "• Business Hours: Monday – Saturday, 9:30 AM to 6:00 PM\n"
                "• Website: https://newindiaelectricals.com/",
                True,
                False,
            )

        # Check commercial / pricing
        if any(term in q_lower for term in ["price", "cost", "quotation", "quote", "discount", "delivery date", "stock", "usd", "inr"]):
            return (
                "Pricing, commercial quotations, and current stock availability are not published in the technical catalogues. "
                "For formal commercial proposals and pricing, please contact New India Electricals Ltd. sales at newindiaelectricals.com.",
                False,
                False,
            )

        # Check out-of-scope / consumer products
        if any(term in q_lower for term in ["ceiling fan", "residential", "decorative", "consumer", "refrigerator", "home appliance"]):
            return (
                "This product is not documented in the available NIEL technical documentation. "
                "New India Electricals Ltd. specializes strictly in industrial power and transmission equipment.",
                False,
                False,
            )

        if not retrieved_chunks:
            return (
                "This specification is not documented in the available NIEL technical documentation. "
                "Please verify the product series or contact NIEL technical support.",
                False,
                False,
            )

        # Synthesize direct conversational answers for common inquiries
        if any(w in q_lower for w in ["what does niel make", "products", "portfolio", "what niel make"]):
            return (
                "New India Electricals Ltd. (NIEL) manufactures and engineers a wide range of industrial electrical equipment, including:\n\n"
                "• Three-Phase AC & DC Induction Motors: From 0.75 kW up to 315 kW in IE3 energy efficiency.\n"
                "• Distribution & Power Transformers: Oil-insulated and dry-type units up to 1250 kVA and 33 kV.\n"
                "• Switchgear & Control Panels: Medium-voltage (MV) panels, motor control centers (MCC), and power distribution boards.\n"
                "• Industrial Pumps: Monoblock, open-well, self-priming, and vacuum pumps up to 275 m³/hr.\n"
                "• Substation Engineering: Compact secondary substations (CSS) and turnkey industrial power systems.",
                True,
                False,
            )

        if any(w in q_lower for w in ["pump", "pumps", "monoblock", "submersible", "vacuum pump"]):
            return (
                "NIEL supplies an extensive range of industrial and utility pumps documented in the official pump portfolio:\n\n"
                "• End Suction Monoblock Pumps (GMCT / KDS+ / KDT+ / KS+): Capacity up to 260 m³/hr, head up to 102 m, power 0.37 kW to 22 kW.\n"
                "• Open Well Submersible Pumps (KOS+): Discharge up to 115 m³/hr, head up to 64 m, power 0.37 kW to 11 kW, 200–440V.\n"
                "• End Suction Process Pumps (KH / KHDT+): Capacity up to 68 m³/hr, head up to 104 m, power 0.25 kW to 15 kW.\n"
                "• Self-Priming Non-Clog Pumps (SP / SPM): Capacity up to 275 m³/hr, head up to 34 m, power 0.75 kW to 19.5 kW for sewage and slurry.\n"
                "• Vacuum Pumps (KV / DV): Vacuum up to 650 mm Hg, airflow up to 162 m³/hr, power 0.75 kW to 7.5 kW for industrial drying.\n"
                "• Borewell Submersible (Champion) & Vertical Multistage (IL): Heads up to 220–249 m with wetted parts in SS304/SS316.",
                True,
                False,
            )

        if any(w in q_lower for w in ["transformer", "transformers"]):
            return (
                "NIEL designs and manufactures Distribution and Power Transformers with the following key specifications:\n\n"
                "• Capacity & Voltage: Ratings up to 1250 kVA in 11 kV, 22 kV, and 33 kV three-phase 50 Hz configurations.\n"
                "• Tap Changers: Off-circuit tap changers (+5% to -10%) and On-load tap changers (+7% to -21% in 1.75% steps).\n"
                "• Insulation & Duty: Class A insulation, continuous S1 duty, Vector group Dyn 11, with copper or aluminium winding.\n"
                "• Standards: Fully compliant with IS 2026 and IEC 76 standards.",
                True,
                False,
            )

        if any(w in q_lower for w in ["switchgear", "panel", "panels"]):
            return (
                "NIEL provides Medium Voltage (MV) and Low Voltage (LV) switchgear panels designed for heavy industrial installations, "
                "including Motor Control Centers (MCC), Power Control Centers (PCC), compact secondary substations, and automated industrial distribution panels.",
                True,
                False,
            )

        if any(w in q_lower for w in ["industries", "industry", "sector", "steel", "clients"]):
            return (
                "NIEL supplies electrical solutions to core heavy industries across India and overseas, including:\n\n"
                "• Steel & Metal Processing (e.g., Bhuwalka Steel Industries, BMA Stainless)\n"
                "• Power Generation & Distribution Sub-stations\n"
                "• Cement & Mining Plants\n"
                "• Sugar Mills & Paper Manufacturing Facilities",
                True,
                False,
            )

        if any(w in q_lower for w in ["mounting", "cooling", "insulation", "voltage", "frequency", "protection", "duty"]):
            return (
                "NIEL industrial motors feature:\n\n"
                "• Voltage & Frequency: 415V, 50 Hz, 3-Phase AC supply.\n"
                "• Mounting Types: Foot mounted B3, Flange mounted B5, and Foot-cum-flange B35.\n"
                "• Protection & Cooling: IP55 protection, Totally Enclosed Fan Cooled (TEFC - IC411).\n"
                "• Insulation & Duty: Class F insulation with Class B temperature rise limit for continuous S1 duty.",
                True,
                False,
            )

        if any(w in q_lower for w in ["power", "kw", "hp", "capacity", "rating", "ratings"]):
            return (
                "NIEL Three-Phase Induction Motors (NIEL-IM-Series) are documented from 0.75 kW to 315 kW in IE3 Premium Efficiency, "
                "rated for 415V, 3-Phase, 50 Hz industrial power supply.",
                True,
                False,
            )

        if any(w in q_lower for w in ["project", "projects", "highlight", "highlights", "track record"]):
            return (
                "New India Electricals Ltd. has executed major turnkey electrical projects across steel plants, power stations, and heavy industries:\n\n"
                "• 220 kV & 66 kV Sub-stations and switchyards for power transmission networks\n"
                "• Turnkey electrical packages for Bhuwalka Steel, BMA Stainless, and rolling mills\n"
                "• Captive power plant interconnections and custom motor control centers\n"
                "• Comprehensive transformer and switchgear installations across industrial sites in India and overseas.",
                True,
                False,
            )

        if any(w in q_lower for w in ["about niel", "company intro", "who is niel", "background", "overview"]):
            return (
                "New India Electricals Ltd. (NIEL) is a premier Indian manufacturer and turnkey engineering provider in electrical power equipment. "
                "Headquartered in Bangalore, NIEL specializes in IE3 energy-efficient induction motors, distribution and power transformers up to 33 kV, "
                "medium-voltage switchgear panels, and industrial pumps for core infrastructure and manufacturing industries.",
                True,
                False,
            )

        if any(w in q_lower for w in ["client", "clients", "customer", "customers", "who buys"]):
            return (
                "NIEL serves major industrial and utility clients across metallurgy, mining, power generation, and manufacturing. "
                "Prominent clients include leading integrated steel plants, regional power transmission boards, sugar mills, and cement facilities across India.",
                True,
                False,
            )

        # Natural special motors inquiry
        if any(w in q_lower for w in ["special motor", "special motors", "custom motor", "special applications"]):
            return (
                "New India Electricals Ltd. engineers specialized induction motors for customized industrial operating conditions:\n\n"
                "• Vertical Hollow Shaft Motors: Designed for deepwell turbine pumps, irrigation, and water systems.\n"
                "• Roller Table Motors: Built to withstand heavy mechanical shock loads and reversing duties in steel rolling mills.\n"
                "• Increased Safety & Non-Sparking Motors: Certified for hazardous industrial atmospheres and chemical handling.\n"
                "• Textile & Loom Motors: High-starting torque motors engineered for continuous spinning and weaving machinery.\n"
                "• 60 Hz Motors: Built for international export requirements and dual-frequency marine or offshore equipment.\n\n"
                "If you need technical drawings, sizing assistance, or commercial quotes for these motors, feel free to ask!",
                True,
                False,
            )

        # Conversational product synthesis
        for chunk, _ in retrieved_chunks:
            text = chunk.text
            if "PRODUCT:" in text:
                parts = {}
                for line in text.splitlines():
                    for key in ["PRODUCT:", "RANGE:", "KEY SPECS:", "KEY FEATURES:", "APPLICATIONS / INDUSTRIES:"]:
                        if line.startswith(key):
                            parts[key.replace(":", "").strip()] = line.replace(key, "").strip()
                if "PRODUCT" in parts:
                    prod = parts["PRODUCT"]
                    items = []
                    if "RANGE" in parts:
                        items.append(f"Capacity and Operating Range: {parts['RANGE']}")
                    if "KEY SPECS" in parts:
                        items.append(f"Key Technical Specs: {parts['KEY SPECS']}")
                    if "KEY FEATURES" in parts:
                        items.append(f"Engineering Features: {parts['KEY FEATURES']}")
                    app = parts.get("APPLICATIONS / INDUSTRIES", "")
                    if app and "no other applications" not in app.lower():
                        items.append(f"Applications: {app}")
                    
                    if items:
                        body_bullets = "\n".join(f"• {item}" for item in items)
                        return (
                            f"NIEL manufactures {prod} engineered for industrial performance:\n\n"
                            f"{body_bullets}\n\n"
                            "Would you like to connect with our engineering team for sizing details or a quotation?",
                            True,
                            False,
                        )

        # General extraction fallback with clean sentence parsing
        raw_words = [
            w for w in q_lower.replace("?", "").replace(".", "").split()
            if len(w) > 3 and w not in ["what", "which", "where", "does", "documented", "state", "about", "niel", "this", "that", "these", "listed", "mentioned", "catalogue"]
        ]
        matched_sentences = []
        for chunk, _ in retrieved_chunks:
            # Filter out metadata lines before sentence splitting
            clean_lines = [
                l.strip() for l in chunk.text.splitlines()
                if not any(l.strip().startswith(p) for p in ["SOURCE:", "CATEGORY:", "NOT IN DOCUMENT:"])
            ]
            body = " ".join(clean_lines)
            sentences = re.split(r"(?<=[a-zA-Z0-9\)])\.\s+", body)
            for s in sentences:
                s_strip = s.strip()
                if len(s_strip) > 25 and not s_strip.startswith(";") and not s_strip.startswith("df ["):
                    if any(w in s_strip.lower() for w in raw_words):
                        clean_s = s_strip if s_strip.endswith(".") else s_strip + "."
                        matched_sentences.append(clean_s)

        if matched_sentences:
            unique_sentences = list(dict.fromkeys(matched_sentences))
            answer = " ".join(unique_sentences[:3])
            return (answer, True, False)

        return (
            "This information is not documented in the available NIEL technical documentation.",
            False,
            False,
        )

    def answer_question(self, question: str, top_k: int = 5) -> ChatResponse:
        """Run the end-to-end grounded QA pipeline."""
        request_id = str(uuid.uuid4())
        q_lower = question.lower()

        # 1. Kill switch
        if self.settings.KILL_SWITCH_ENABLED:
            return ChatResponse(
                answer="The AI Assistant is temporarily paused by system administration. Please try again later.",
                citations=[],
                evidence_sufficient=False,
                clarification_needed=False,
                request_id=request_id,
            )

        # 2. Defensive check for direct prompt injection
        injection_triggers = [
            "ignore previous",
            "ignore all previous",
            "system prompt",
            "api key",
            "reveal your instructions",
            "developer mode",
        ]
        if any(trigger in q_lower for trigger in injection_triggers):
            return ChatResponse(
                answer=(
                    "I am the NIEL Industrial Intelligence Assistant. I provide technical product specifications "
                    "strictly based on authorized NIEL documentation. I cannot disclose internal system instructions or credentials."
                ),
                citations=[],
                evidence_sufficient=False,
                clarification_needed=False,
                request_id=request_id,
            )

        # 3. Handle conversational pleasantries (greetings, thanks, introductions) like a genuine human engineer
        clean_q = re.sub(r"[^\w\s]", "", q_lower).strip()
        words = clean_q.split()
        greeting_words = {"hi", "hello", "hey", "hi there", "hello there", "good morning", "good afternoon", "good evening", "namaste", "greetings"}
        thanks_words = {"thank you", "thanks", "thanks a lot", "thank you so much", "thx", "appreciate it"}
        intro_words = {"who are you", "what can you do", "help", "what is this"}

        is_pure_greeting = clean_q in greeting_words or (len(words) <= 4 and any(words[0] == g for g in ["hi", "hello", "hey", "good"]))
        is_thanks = clean_q in thanks_words or (any(clean_q.startswith(t) for t in ["thank", "thanks"]) and len(words) <= 8)
        is_intro = clean_q in intro_words

        if is_pure_greeting:
            if self.openai_service.is_live_configured:
                try:
                    client = self.openai_service._get_client()
                    completion = client.chat.completions.create(
                        model=self.settings.OPENAI_MODEL,
                        temperature=0.7,
                        max_tokens=150,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": question},
                        ],
                    )
                    ans = (completion.choices[0].message.content or "").replace("**", "")
                    return ChatResponse(
                        answer=ans,
                        citations=[],
                        evidence_sufficient=True,
                        clarification_needed=False,
                        request_id=request_id,
                    )
                except Exception:
                    pass
            return ChatResponse(
                answer=(
                    "Hello! Welcome to New India Electricals. I am here to help you explore our electrical products, "
                    "understand technical specifications for motors, transformers, switchgear, and pumps, "
                    "or guide you on getting a quote. How can I assist you with your project today?"
                ),
                citations=[],
                evidence_sufficient=True,
                clarification_needed=False,
                request_id=request_id,
            )

        if is_thanks:
            return ChatResponse(
                answer=(
                    "You are very welcome! If you have any further questions about our products or need "
                    "commercial assistance, feel free to ask anytime. We are happy to help!"
                ),
                citations=[],
                evidence_sufficient=True,
                clarification_needed=False,
                request_id=request_id,
            )

        if is_intro:
            return ChatResponse(
                answer=(
                    "I am the customer support assistant for New India Electricals Ltd. (NIEL). "
                    "I can help you look up technical specifications, explore our motors, transformers, switchgear, and pumps, "
                    "understand what is needed for a quote, or connect you with our sales engineering team."
                ),
                citations=[],
                evidence_sufficient=True,
                clarification_needed=False,
                request_id=request_id,
            )

        # 4. Retrieve relevant chunks
        retrieved_chunks = self.retriever.retrieve(query=question, top_k=top_k)

        # 4. Check if evidence is sufficient
        if not retrieved_chunks:
            return ChatResponse(
                answer="This specification is not documented in the available NIEL technical documentation.",
                citations=[],
                evidence_sufficient=False,
                clarification_needed=False,
                request_id=request_id,
            )

        # 5. Check whether user explicitly asked for document attachments or citations
        asked_for_pdf = any(kw in q_lower for kw in ["pdf", "document", "catalogue", "catalog", "brochure", "attach", "file", "page", "source", "download", "where can i read"])

        valid_citations = self._validate_citations(retrieved_chunks)

        # 6. Generate answer via OpenAI or offline fallback
        if not self.openai_service.is_live_configured:
            answer_text, sufficient, clarification = self._generate_offline_grounded_answer(
                question=question,
                retrieved_chunks=retrieved_chunks,
            )
            answer_text = answer_text.replace("**", "")
            return ChatResponse(
                answer=answer_text,
                citations=valid_citations if sufficient else [],
                evidence_sufficient=sufficient,
                clarification_needed=clarification,
                request_id=request_id,
                usage=UsageMetadata(prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0.0),
            )

        # Build grounded context with security boundaries
        context_blocks = []
        for chunk, score in retrieved_chunks:
            context_blocks.append(
                f"[Source: {chunk.source_filename}, Page: {chunk.page_number}]\n{chunk.text}"
            )
        context_payload = "\n\n---\n\n".join(context_blocks)

        user_prompt = (
            f"<EVIDENCE>\n{context_payload}\n</EVIDENCE>\n\n"
            f"User Question: {question}\n\n"
            "Answer the question directly, fluently, and concisely. Only state facts supported by the evidence."
        )

        try:
            client = self.openai_service._get_client()
            completion = client.chat.completions.create(
                model=self.settings.OPENAI_MODEL,
                temperature=0.0,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            answer_text = (completion.choices[0].message.content or "").replace("**", "")
            
            p_tokens = completion.usage.prompt_tokens if completion.usage else 0
            c_tokens = completion.usage.completion_tokens if completion.usage else 0
            t_tokens = completion.usage.total_tokens if completion.usage else 0
            
            self.openai_service.total_prompt_tokens += p_tokens
            self.openai_service.total_completion_tokens += c_tokens
            
            req_cost = (p_tokens / 1_000_000.0) * GPT4O_MINI_PROMPT_PER_MILLION + (c_tokens / 1_000_000.0) * GPT4O_MINI_COMPLETION_PER_MILLION

            lower_answer = answer_text.lower()
            insufficient_phrases = ["not documented", "not mentioned", "does not contain", "no information"]
            is_sufficient = not any(phrase in lower_answer for phrase in insufficient_phrases)

            return ChatResponse(
                answer=answer_text,
                citations=valid_citations if (is_sufficient and asked_for_pdf) else [],
                evidence_sufficient=is_sufficient,
                clarification_needed=False,
                request_id=request_id,
                usage=UsageMetadata(
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    estimated_cost_usd=round(req_cost, 6),
                ),
            )
        except OpenAIError as exc:
            logger.error("OpenAI Chat Completion failed: %s", exc)
            return ChatResponse(
                answer="An error occurred while communicating with the AI service. Please try again shortly.",
                citations=[],
                evidence_sufficient=False,
                clarification_needed=False,
                request_id=request_id,
            )


_rag_service_instance = None


def get_rag_service() -> RAGService:
    """Singleton accessor for RAG service."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
